import { Suspense } from "react";
import styles from "./page.module.css";
import RefreshButton from "./RefreshButton";

type Product = {
    id: number;
    name: string;
    image_key: string;
    image_url: string;
};

// функция получения товаров
async function getProducts(): Promise<Product[]> {
    const apiUrl = process.env.CATALOG_API_URL;

    if (!apiUrl) {
        throw new Error("CATALOG_API_URL is not configured");
    }

    const response = await fetch(`${apiUrl}/products`, {
        cache: "no-store",
    });

    if (!response.ok) {
        throw new Error("Failed to fetch products");
    }

    return response.json();
}

// функция списка товаров
async function ProductsList() {
    const products = await getProducts();

    if (products.length === 0) {
        return (
            <div className={styles.state}>
                <p>Товаров пока нет</p>
            </div>
        );
    }

    return (
        <div className={styles.grid}>
            {products.map((product) => (
                <article className={styles.card} key={product.id}>
                    <img
                        className={styles.image}
                        src={product.image_url}
                        alt={product.name}
                        loading="lazy"
                    />

                    <h2 className={styles.productName}>
                        {product.name}
                    </h2>
                </article>
            ))}
        </div>
    );
}

// компонент страницы товаров

export default function HomePage() {
    return (
        <main className={styles.page}>
            <div className={styles.heading}>
                <h1>Каталог</h1>
                <RefreshButton />
            </div>

            <Suspense
                fallback={
                    <div className={styles.state} role="status">
                        Загружаем товары...
                    </div>
                }
            >
                <ProductsList />
            </Suspense>
        </main>
    );
}
