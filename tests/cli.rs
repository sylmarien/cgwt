use std::process::{Command, Output};

fn run_cgwt(arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_cgwt"))
        .args(arguments)
        .output()
        .expect("the cgwt binary runs")
}

#[test]
fn version_flag_prints_the_package_version() {
    let output = run_cgwt(&["--version"]);

    assert_eq!(output.status.code(), Some(0));
    assert_eq!(
        String::from_utf8_lossy(&output.stdout),
        format!("cgwt {}\n", env!("CARGO_PKG_VERSION"))
    );
}

#[test]
fn missing_arguments_print_usage_and_exit_with_2() {
    let output = run_cgwt(&[]);

    assert_eq!(output.status.code(), Some(2));
    assert_eq!(
        String::from_utf8_lossy(&output.stderr),
        "usage: cgwt --version\n"
    );
}
