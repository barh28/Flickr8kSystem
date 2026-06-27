import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/context";
import Button from "../components/common/Button";
import Spinner from "../components/common/Spinner";
import TextField from "../components/common/TextField";
import ThemeToggle from "../components/common/ThemeToggle";
import styles from "./css/LoginPage.module.css";

type Mode = "login" | "register";

interface LocationState {
  from?: { pathname?: string };
}

// Must match the backend constraints (users service).
const USERNAME_MIN = 3;
const USERNAME_MAX = 50;
const PASSWORD_MIN = 4;
const PASSWORD_MAX = 128;

export default function LoginPage() {
  const { isAuthenticated, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const from = (location.state as LocationState)?.from?.pathname ?? "/";

  const mutation = useMutation({
    mutationFn: () =>
      mode === "login" ? login(username, password) : register(username, password),
    onSuccess: () => navigate(from, { replace: true }),
  });

  // Validate on the client so we never trigger native browser validation
  // bubbles and can keep the submit button disabled until the form is valid.
  // Messages only show once a field has content, to avoid yelling on an empty form.
  const trimmedUsername = username.trim();
  const usernameError =
    trimmedUsername.length === 0
      ? ""
      : trimmedUsername.length < USERNAME_MIN
        ? `Username must be at least ${USERNAME_MIN} characters.`
        : trimmedUsername.length > USERNAME_MAX
          ? `Username must be at most ${USERNAME_MAX} characters.`
          : "";
  const passwordError =
    password.length === 0
      ? ""
      : password.length < PASSWORD_MIN
        ? `Password must be at least ${PASSWORD_MIN} characters.`
        : password.length > PASSWORD_MAX
          ? `Password must be at most ${PASSWORD_MAX} characters.`
          : "";
  const isValid =
    trimmedUsername.length >= USERNAME_MIN &&
    trimmedUsername.length <= USERNAME_MAX &&
    password.length >= PASSWORD_MIN &&
    password.length <= PASSWORD_MAX;

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  function switchMode() {
    setMode((current) => (current === "login" ? "register" : "login"));
    mutation.reset();
  }

  function renderFace(faceMode: Mode) {
    const active = faceMode === mode;
    const isLogin = faceMode === "login";
    return (
      <div
        className={`${styles.face} ${isLogin ? "" : styles.back}`}
        inert={!active}
        aria-hidden={!active}
      >
        <div className={styles.brand}>
          <span className={styles.logo} aria-hidden />
          <h1 className={styles.title}>Flickr8k Explorer</h1>
        </div>
        <p className={styles.subtitle}>
          {isLogin
            ? "Sign in to browse and tag the dataset."
            : "Create an account to start tagging."}
        </p>

        <form
          className={styles.form}
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            if (!isValid) return;
            mutation.mutate();
          }}
        >
          <div className={styles.field}>
            <TextField
              label="Username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              autoFocus={active && isLogin}
              aria-invalid={usernameError ? true : undefined}
            />
            {usernameError && <span className={styles.fieldError}>{usernameError}</span>}
          </div>
          <div className={styles.field}>
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={isLogin ? "current-password" : "new-password"}
              aria-invalid={passwordError ? true : undefined}
            />
            {passwordError && <span className={styles.fieldError}>{passwordError}</span>}
          </div>

          <Button type="submit" block disabled={mutation.isPending || !isValid}>
            {mutation.isPending ? <Spinner /> : isLogin ? "Sign in" : "Create account"}
          </Button>
        </form>

        <p className={styles.switch}>
          {isLogin ? "No account yet? " : "Already have an account? "}
          <button type="button" className={styles.switchButton} onClick={switchMode}>
            {isLogin ? "Create one" : "Sign in"}
          </button>
        </p>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.topRight}>
        <ThemeToggle />
      </div>
      <div className={styles.scene}>
        <div className={`${styles.card} ${mode === "register" ? styles.flipped : ""}`}>
          {renderFace("login")}
          {renderFace("register")}
        </div>
      </div>
    </div>
  );
}
