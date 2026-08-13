import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_XCCONFIG = "COUNSELOR_API_BASE_URL = https:/$()/counselor-agent-web.onrender.com/"
EXPECTED_SERVICE = {
    "type": "web",
    "name": "counselor-agent-web",
    "runtime": "python",
    "plan": "free",
    "buildCommand": "pip install -r requirements.txt",
    "startCommand": "python scripts/web_workbench.py --host 0.0.0.0 --port $PORT",
    "healthCheckPath": "/health",
}
EXPECTED_RENDER_ENV_VARS = [
    {"key": "DEEPSEEK_API_KEY", "sync": "false"},
    {"key": "DEEPSEEK_BASE_URL", "value": "https://api.deepseek.com"},
    {"key": "DEEPSEEK_MODEL", "value": "deepseek-v4-flash"},
    {"key": "DEEPSEEK_TIMEOUT_SECONDS", "value": '"120"'},
    {"key": "WORKBENCH_USER", "sync": "false"},
    {"key": "WORKBENCH_PASSWORD", "sync": "false"},
    {"key": "WORKBENCH_ALLOW_SIGNUP", "value": '"false"'},
    {"key": "WORKBENCH_SIGNUP_INVITE_CODE", "sync": "false"},
    {"key": "WORKBENCH_MAX_UPLOAD_BYTES", "value": '"10485760"'},
    {"key": "WORKBENCH_RETENTION_DAYS", "value": '"14"'},
]
EXPECTED_ENV_EXAMPLE = {
    "DEEPSEEK_API_KEY": "",
    "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
    "DEEPSEEK_MODEL": "deepseek-v4-flash",
    "DEEPSEEK_TIMEOUT_SECONDS": "120",
    "WORKBENCH_USER": "",
    "WORKBENCH_PASSWORD": "",
    "WORKBENCH_ALLOW_SIGNUP": "",
    "WORKBENCH_SIGNUP_INVITE_CODE": "",
    "WORKBENCH_MAX_UPLOAD_BYTES": "",
    "WORKBENCH_RETENTION_DAYS": "",
}


def parse_single_render_service(blueprint):
    lines = blueprint.splitlines()
    if not lines or lines[0] != "services:":
        raise ValueError("Blueprint must begin with services:.")

    service_starts = [
        index for index, line in enumerate(lines) if line.startswith("  - ")
    ]
    if len(service_starts) != 1:
        raise ValueError("Blueprint must declare exactly one service.")

    service_lines = lines[service_starts[0] :]
    fields = {}
    env_vars_index = None
    for index, line in enumerate(service_lines):
        if line == "    envVars:":
            env_vars_index = index
            break
        if index == 0:
            key, value = line.removeprefix("  - ").split(": ", maxsplit=1)
        else:
            if not line.startswith("    ") or ": " not in line:
                raise ValueError(f"Invalid service field: {line}")
            key, value = line[4:].split(": ", maxsplit=1)
        fields[key] = value

    if env_vars_index is None:
        raise ValueError("Service must declare envVars.")

    env_vars = []
    index = env_vars_index + 1
    while index < len(service_lines):
        key_line = service_lines[index]
        if not key_line.startswith("      - key: "):
            raise ValueError(f"Invalid env key: {key_line}")
        if index + 1 >= len(service_lines):
            raise ValueError("Environment variable is missing its value or sync setting.")
        setting_line = service_lines[index + 1]
        if not setting_line.startswith("        ") or ": " not in setting_line:
            raise ValueError(f"Invalid env setting: {setting_line}")
        setting, value = setting_line[8:].split(": ", maxsplit=1)
        if setting not in ("value", "sync"):
            raise ValueError(f"Unexpected env setting: {setting}")
        env_vars.append({"key": key_line.removeprefix("      - key: "), setting: value})
        index += 2

    return fields, env_vars


class DeploymentContractTest(unittest.TestCase):
    def test_render_blueprint_declares_only_the_web_product(self):
        blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")
        service, env_vars = parse_single_render_service(blueprint)
        self.assertEqual(service, EXPECTED_SERVICE)
        self.assertEqual(env_vars, EXPECTED_RENDER_ENV_VARS)

    def test_ios_build_variants_use_the_web_product_host(self):
        for relative in ("ios-app/Config/Debug.xcconfig", "ios-app/Config/Release.xcconfig"):
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(EXPECTED_XCCONFIG, content)

    def test_environment_example_keeps_required_product_configuration(self):
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        assignments = dict(
            line.split("=", maxsplit=1)
            for line in example.splitlines()
            if line and not line.startswith("#") and "=" in line
        )
        self.assertEqual(
            {name: assignments.get(name) for name in EXPECTED_ENV_EXAMPLE},
            EXPECTED_ENV_EXAMPLE,
        )


if __name__ == "__main__":
    unittest.main()
