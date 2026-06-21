use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use tauri::{
    image::Image,
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::TrayIconBuilder,
    Manager,
};
use tauri_plugin_shell::ShellExt;

struct AppState {
    child: Mutex<Option<tauri_plugin_shell::process::CommandChild>>,
    should_stop: Arc<AtomicBool>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            // Second instance launched: focus the existing window instead
            if let Some(w) = app.get_webview_window("main") {
                let _ = w.show();
                let _ = w.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Build tray menu: Open | --- | Quit
            let open = MenuItem::with_id(app, "open", "Open", true, None::<&str>)?;
            let sep = PredefinedMenuItem::separator(app)?;
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open, &sep, &quit])?;

            // Load amber icon (starting state); fall back to the default window icon
            let resource_dir = app.path().resource_dir()?;
            let amber_icon = Image::from_path(resource_dir.join("icons/tray-amber.png"))
                .ok()
                .or_else(|| app.default_window_icon().cloned());

            let Some(amber_icon) = amber_icon else {
                return Err("No usable tray icon found. Ensure icons/icon.png is configured in tauri.conf.json".into());
            };

            TrayIconBuilder::with_id("main")
                .icon(amber_icon)
                .menu(&menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" => {
                        if let Some(w) = app.get_webview_window("main") {
                            let _ = w.show();
                            let _ = w.set_focus();
                        }
                    }
                    "quit" => {
                        // Signal background threads to stop, then kill sidecar and exit
                        if let Some(state) = app.try_state::<AppState>() {
                            state.should_stop.store(true, Ordering::Relaxed);
                            if let Ok(mut lock) = state.child.lock() {
                                if let Some(child) = lock.take() {
                                    let _ = child.kill();
                                }
                            }
                        }
                        app.exit(0);
                    }
                    _ => {}
                })
                .build(app)?;

            let stop_flag = Arc::new(AtomicBool::new(false));

            // Spawn sidecar
            match app
                .shell()
                .sidecar("aaplamanus-server")
                .and_then(|cmd| cmd.spawn())
            {
                Ok((rx, child)) => {
                    // Drain sidecar output on a thread to prevent pipe-buffer deadlock.
                    // Uvicorn writes startup logs to stderr; without draining, the buffer
                    // fills and the server blocks before binding to port 5172.
                    std::thread::spawn(move || {
                        while rx.recv().is_ok() {}
                    });
                    app.manage(AppState {
                        child: Mutex::new(Some(child)),
                        should_stop: Arc::clone(&stop_flag),
                    });
                }
                Err(e) => {
                    eprintln!("Failed to start sidecar: {e}");
                    app.manage(AppState {
                        child: Mutex::new(None),
                        should_stop: Arc::clone(&stop_flag),
                    });
                    // Tray turns red so user sees failure state, not "starting"
                    if let Some(tray) = app.handle().tray_by_id("main") {
                        if let Ok(dir) = app.path().resource_dir() {
                            if let Ok(icon) = Image::from_path(dir.join("icons/tray-red.png")) {
                                let _ = tray.set_icon(Some(icon));
                            }
                        }
                    }
                }
            }

            // Health check loop runs in a background thread so setup() returns immediately
            let handle = app.handle().clone();
            let flag = Arc::clone(&stop_flag);
            std::thread::spawn(move || poll_until_ready(handle, flag));

            Ok(())
        })
        .on_window_event(|window, event| {
            // Closing the main window hides it instead of quitting the app.
            // Scoped to "main" so future dialogs/panels close normally.
            if window.label() == "main" {
                if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                    api.prevent_close();
                    let _ = window.hide();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("failed to run app");
}

/// Load a tray status icon from the bundled resources directory.
fn set_tray_icon(app: &tauri::AppHandle, icon_file: &str) {
    if let Some(tray) = app.tray_by_id("main") {
        if let Ok(dir) = app.path().resource_dir() {
            if let Ok(icon) = Image::from_path(dir.join(format!("icons/{icon_file}"))) {
                let _ = tray.set_icon(Some(icon));
            }
        }
    }
}

/// Polls TCP port 5172 every 500ms until the FastAPI server is ready (or 30s timeout).
/// Updates the tray icon to green on success, red on timeout.
/// Accepts a stop flag so the Quit handler can abort the loop before app teardown.
fn poll_until_ready(app: tauri::AppHandle, should_stop: Arc<AtomicBool>) {
    let addr: std::net::SocketAddr = "127.0.0.1:5172".parse().unwrap();
    let start = std::time::Instant::now();
    let timeout = std::time::Duration::from_secs(60);

    loop {
        if should_stop.load(Ordering::Relaxed) {
            // App is shutting down; exit without touching the tray
            break;
        }

        if start.elapsed() > timeout {
            set_tray_icon(&app, "tray-red.png");
            break;
        }

        // A successful TCP connection means the server is accepting connections
        if std::net::TcpStream::connect_timeout(
            &addr,
            std::time::Duration::from_millis(100),
        )
        .is_ok()
        {
            // Wait 1s for Uvicorn to finish loading routes after binding the port
            std::thread::sleep(std::time::Duration::from_secs(3));
            set_tray_icon(&app, "tray-green.png");
            if let Some(w) = app.get_webview_window("main") {
                let _ = w.show();
                let _ = w.set_focus();
            }
            break;
        }

        std::thread::sleep(std::time::Duration::from_millis(500));
    }
}
