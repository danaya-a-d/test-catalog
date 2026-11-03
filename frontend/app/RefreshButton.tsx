
"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import styles from "./page.module.css";

export default function RefreshButton() {
    const router = useRouter();
    const [isPending, startTransition] = useTransition();

    const handleRefresh = () => {
        startTransition(() => {
            router.refresh();
        });
    };

    return (
        <button
            type="button"
            className={styles.refreshButton}
            onClick={handleRefresh}
            disabled={isPending}
        >
            {isPending ? "Обновляем..." : "↻ Обновить"}
        </button>
    );
}
