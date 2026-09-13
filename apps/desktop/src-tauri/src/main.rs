use std::env;
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use tauri::Manager;

fn bundled_engine_path(app: &tauri::AppHandle) -> Option<PathBuf> {
    let resource_dir = app.path().resource_dir().ok()?;
    let candidate = resource_dir.join("resources").join("lumen-engine.exe");
    candidate.is_file().then_some(candidate)
}

fn engine_command(app: &tauri::AppHandle) -> Result<(Command, String), String> {
    if let Ok(python) = env::var("LUMEN_PYTHON") {
        let mut command = Command::new(&python);
        command.arg("-m").arg("lumen_lab.desktop_bridge");
        return Ok((command, format!("Python override '{python}'")));
    }

    if let Some(engine) = bundled_engine_path(app) {
        let label = engine.display().to_string();
        return Ok((Command::new(engine), label));
    }

    if cfg!(debug_assertions) {
        let python = "python".to_string();
        let mut command = Command::new(&python);
        command.arg("-m").arg("lumen_lab.desktop_bridge");
        return Ok((command, "development Python engine".to_string()));
    }

    Err(
        "Lumen's bundled engine is missing from this installation. Reinstall Lumen and try again."
            .to_string(),
    )
}

#[tauri::command]
fn lumen_request(app: tauri::AppHandle, request: String) -> Result<String, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|error| format!("could not resolve app data directory: {error}"))?;

    fs::create_dir_all(&data_dir)
        .map_err(|error| format!("could not create app data directory: {error}"))?;

    let (mut command, engine_label) = engine_command(&app)?;

    // The desktop bridge speaks JSON over stdio. On Windows, Python can otherwise
    // inherit the active ANSI code page (for example Windows-1251), while Tauri
    // expects UTF-8. Force a stable encoding in both development and bundled builds.
    command
        .env("PYTHONIOENCODING", "utf-8")
        .env("PYTHONUTF8", "1");

    let mut child = command
        .current_dir(&data_dir)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("could not start Lumen engine ({engine_label}): {error}"))?;

    if let Some(stdin) = child.stdin.as_mut() {
        stdin
            .write_all(request.as_bytes())
            .map_err(|error| format!("could not send request to Lumen engine: {error}"))?;
    }

    let output = child
        .wait_with_output()
        .map_err(|error| format!("Lumen engine did not finish correctly: {error}"))?;

    let stdout = String::from_utf8(output.stdout)
        .map_err(|error| format!("Lumen engine returned invalid UTF-8: {error}"))?;

    if !stdout.trim().is_empty() {
        return Ok(stdout);
    }

    let stderr = String::from_utf8_lossy(&output.stderr);
    Err(if stderr.trim().is_empty() {
        "Lumen engine returned no response".to_string()
    } else {
        stderr.trim().to_string()
    })
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![lumen_request])
        .run(tauri::generate_context!())
        .expect("error while running Lumen desktop application");
}
