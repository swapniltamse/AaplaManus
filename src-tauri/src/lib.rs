use std::sync::Mutex;
use tauri::{
    image::Image,
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::TrayIconBuilder,
    Manager,
};
use tauri_plugin_shell::ShellExt;

struct AppState {
    child: Mutex<Option<tauri_plugin_shell::process::CommandChild>>,
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
            let amber_icon =
                Image::from_path(resource_dir.join("icons/tray-amber.png"))
                    .unwrap_or_else(|_| app.default_window_icon().unwrap().clone());

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
                        // Kill sidecar before exit so the Python process doesn't linger
                        if let Some(state) = app.try_state::<AppState>() {
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

            // Spawn sidecar
            match app
                .shell()
                .sidecar("aaplamanus-server")
                .and_then(|cmd| cmd.spawn())
            {
                Ok((rx, child)) => {
                    drop(rx); // We don't need stdout/stderr from the sidecar here
                    app.manage(AppState {
                        child: Mutex::new(Some(child)),
                    });
                }
                Err(e) => {
                    eprintln!("Failed to start sidecar: {e}");
                    app.manage(AppState {
                        child: Mutex::new(None),
                    });
                    // Tray stays amber; user can Quit and investigate
                }
            }

            // Health check loop runs in a background thread so setup() returns immediately
            let handle = app.handle().clone();
            std::thread::spawn(move || poll_until_ready(handle));

            Ok(())
        })
        .on_window_event(|window, event| {
            // Closing the window hides it instead of quitting the app
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
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
fn poll_until_ready(app: tauri::AppHandle) {
    let addr: std::net::SocketAddr = "127.0.0.1:5172".parse().unwrap();
    let start = std::time::Instant::now();
    let timeout = std::time::Duration::from_secs(30);

    loop {
        if start.elapsed() > timeout {
            set_tray_icon(&app, "tray-red.png");
            break;
        }

        // A successful TCP connection means FastAPI is accepting HTTP requests
        if std::net::TcpStream::connect_timeout(
            &addr,
            std::time::Duration::from_millis(100),
        )
        .is_ok()
        {
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
