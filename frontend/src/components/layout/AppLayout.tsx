import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../../auth/context";
import Button from "../common/Button";
import ThemeToggle from "../common/ThemeToggle";
import styles from "./css/AppLayout.module.css";

export default function AppLayout() {
  const { user, logout } = useAuth();

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `${styles.navLink} ${isActive ? styles.navLinkActive : ""}`;

  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <span className={styles.logo} aria-hidden />
          <span>Flickr8k Explorer</span>
        </div>
        <nav className={styles.nav}>
          <NavLink to="/" end className={navClass}>
            Explorer
          </NavLink>
          <NavLink to="/stats" className={navClass}>
            Statistics
          </NavLink>
        </nav>
        <div className={styles.actions}>
          <ThemeToggle />
          <div className={styles.user}>
            {user && (
              <span className={styles.userText}>
                Signed in as <span className={styles.username}>{user.username}</span>
              </span>
            )}
            <Button variant="ghost" onClick={logout}>
              Log out
            </Button>
          </div>
        </div>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
