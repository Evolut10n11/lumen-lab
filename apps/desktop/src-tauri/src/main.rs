use std::env;
use std::fs;
use std::io::Write;
use std::process::{Command, Stdio};
use tauri::Manager;

#[tauri::command]
fn lumen_request(app: tauri::AppHandle, request: String) -> Result<String, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|error| format!("could not resolve app data directory: {error}"))?;

    fs::create_dir_all(&data_dir)
        .map_err(|error| format!("could not create app data directory: {error}"))?;

    let python = env::var("LUMEN_PYTHON").unwrap_or_else(|_| "python".to_string());
    let mut child = Command::new(&python)
        .arg("-m")
        .arg("lumen_lab.desktop_bridge")
        .current_dir(&data_dir)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| {
            format!(
                "could not start the Lumen engine with '{python}': {error}. \
                 Activate the project virtual environment or set LUMEN_PYTHON."
            )
        })?;

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
