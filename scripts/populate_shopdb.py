#!/usr/bin/env python3
"""Generate realistic sample data for shopdb for chatbot context."""

import random
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

# Database connection
DB_HOST = "10.0.1.189"
DB_PORT = 5432
DB_NAME = "shopdb"
DB_USER = "monitoring"
DB_PASSWORD = "changeme"

CUSTOMER_COUNT = 500
PRODUCT_COUNT = 50
ORDER_COUNT = 5000


def connect_db():
    """Connect to PostgreSQL."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def generate_customers():
    """Generate customer records."""
    first_names = [
        "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
        "Iris", "Jack", "Karen", "Liam", "Mia", "Noah", "Olivia", "Peter",
    ]
    last_names = [
        "Smith", "Johnson", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor",
        "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Lee", "Garcia",
    ]

    customers = []
    for i in range(CUSTOMER_COUNT):
        first = random.choice(first_names)
        last = random.choice(last_names)
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        city = random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"])
        customers.append((f"{first} {last}", email, city))

    return customers


def generate_products():
    """Generate product catalog."""
    categories = ["Electronics", "Clothing", "Books", "Home & Garden", "Sports"]
    product_names = {
        "Electronics": ["Laptop", "Phone", "Tablet", "Headphones", "Monitor", "Keyboard", "Mouse"],
        "Clothing": ["T-Shirt", "Jeans", "Jacket", "Shoes", "Hat", "Socks"],
        "Books": ["Python Guide", "Database Design", "Web Dev", "Cloud Computing", "AI Basics"],
        "Home & Garden": ["Lamp", "Chair", "Table", "Plant Pot", "Curtains"],
        "Sports": ["Running Shoes", "Yoga Mat", "Dumbbell", "Water Bottle", "Tennis Racket"],
    }

    products = []
    for category in categories:
        for name in product_names[category]:
            price = round(random.uniform(10, 500), 2)
            stock = random.randint(0, 1000)
            products.append((name, category, price, stock))

    return products


def generate_orders(conn, customer_count, product_count):
    """Generate order records with realistic patterns."""
    orders = []
    order_items = []

    base_date = datetime.now() - timedelta(days=365)

    for order_id in range(1, ORDER_COUNT + 1):
        customer_id = random.randint(1, customer_count)
        order_date = base_date + timedelta(days=random.randint(0, 365))
        status = random.choice(["pending", "completed", "shipped", "cancelled"])

        orders.append((order_id, customer_id, order_date, status))

        # Add 1-5 items per order
        item_count = random.randint(1, 5)
        for item_idx in range(item_count):
            product_id = random.randint(1, product_count)
            quantity = random.randint(1, 10)
            price = round(random.uniform(10, 500), 2)
            order_items.append((order_id, product_id, quantity, price))

    # Insert orders and order items
    cursor = conn.cursor()
    try:
        execute_values(
            cursor,
            """INSERT INTO orders (order_id, customer_id, order_date, status)
               VALUES %s ON CONFLICT DO NOTHING""",
            orders,
        )

        execute_values(
            cursor,
            """INSERT INTO order_items (order_id, product_id, quantity, price)
               VALUES %s ON CONFLICT DO NOTHING""",
            order_items,
        )

        conn.commit()
        print(f"✓ Generated {len(orders)} orders with {len(order_items)} items")
    finally:
        cursor.close()


def main():
    """Populate the database."""
    print("Generating sample data for shopdb...")

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(100),
                city VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                category VARCHAR(50),
                price DECIMAL(10, 2),
                stock INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER REFERENCES customers(customer_id),
                order_date TIMESTAMP,
                status VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                item_id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES orders(order_id),
                product_id INTEGER REFERENCES products(product_id),
                quantity INTEGER,
                price DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        print("✓ Tables created")

        # Check if data already exists
        cursor.execute("SELECT COUNT(*) FROM customers")
        if cursor.fetchone()[0] > 0:
            print("✓ Data already exists, skipping population")
            return

        # Generate and insert customers
        customers = generate_customers()
        execute_values(
            cursor,
            "INSERT INTO customers (name, email, city) VALUES %s",
            customers,
        )
        conn.commit()
        print(f"✓ Generated {len(customers)} customers")

        # Generate and insert products
        products = generate_products()
        execute_values(
            cursor,
            "INSERT INTO products (name, category, price, stock) VALUES %s",
            products,
        )
        conn.commit()
        print(f"✓ Generated {len(products)} products")

        # Generate and insert orders
        generate_orders(conn, CUSTOMER_COUNT, PRODUCT_COUNT)

        print("\n✓ Database population complete!")

    except Exception as e:
        print(f"✗ Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
