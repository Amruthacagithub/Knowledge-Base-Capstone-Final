from scripts import write_cloudrun_env


def test_cloudrun_env_writer_excludes_secret_values(tmp_path, monkeypatch):
    monkeypatch.setattr(write_cloudrun_env, "PROJECT_ROOT", tmp_path)
    (tmp_path / ".env").write_text(
        "DATABASE_URL=synthetic-database-secret\n"
        "JWT_SECRET=synthetic-jwt-secret\n"
        "GEMINI_API_KEY=synthetic-gemini-secret\n"
        "AUTH_MODE=password\n"
        "CORS_ORIGINS=https://frontend.example\n",
        encoding="utf-8",
    )

    write_cloudrun_env.main()

    output = (tmp_path / "deploy" / "cloudrun.env.yaml").read_text(encoding="utf-8")
    assert "AUTH_MODE" in output
    assert "CORS_ORIGINS" in output
    assert "synthetic" not in output
    assert write_cloudrun_env.SECRET_KEYS.isdisjoint(
        write_cloudrun_env.NON_SECRET_KEYS
    )