"use client";

import styles from "./page.module.css";

type ErrorProps = {
    unstable_retry: () => void;
};

export default function ErrorPage({
                                      unstable_retry,
                                  }: ErrorProps) {
    return (
        <main className={styles.page}>
            <h1 className={styles.title}>Каталог</h1>

            <div className={styles.state} role="alert">
                <p>Не удалось загрузить товары</p>

                <button
                    type="button"
                    className={styles.retryButton}
                    onClick={unstable_retry}
                >
                    Попробовать снова
                </button>
            </div>
        </main>
    );
}
