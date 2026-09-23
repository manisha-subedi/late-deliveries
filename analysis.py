"""Late deliveries and bad reviews. Olist orders, 2016 to 2018. Run: python analysis.py"""

from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt

DATA = Path("data")
CHARTS = Path("charts")


def connect(data_dir: Path = DATA) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for name in ["orders", "order_reviews", "order_items", "customers"]:
        con.execute(f"create view {name} as select * from read_csv('{data_dir}/olist_{name}_dataset.csv')")

    con.execute("""
        create view delivered as
        select order_id,
               customer_id,
               cast(order_purchase_timestamp as date) as ordered,
               cast(order_delivered_customer_date as date) as delivered,
               cast(order_estimated_delivery_date as date) as promised,
               datediff('day', cast(order_estimated_delivery_date as date),
                               cast(order_delivered_customer_date as date)) as days_late
        from orders
        where order_status = 'delivered' and order_delivered_customer_date is not null
    """)

    # a few orders have two reviews. keep the newest one.
    con.execute("""
        create view review as
        select order_id, review_score
        from (
            select order_id, review_score,
                   row_number() over (partition by order_id order by review_answer_timestamp desc) as n
            from order_reviews
        )
        where n = 1
    """)
    return con


def late_share(con):
    return con.execute("""
        select count(*) as orders,
               sum(case when days_late > 0 then 1 else 0 end) as late,
               round(100.0 * sum(case when days_late > 0 then 1 else 0 end) / count(*), 1) as late_pct
        from delivered
    """).fetchone()


def score_by_lateness(con):
    return con.execute("""
        select case when days_late <= 0 then 'on time'
                    when days_late <= 3 then '1 to 3 days late'
                    when days_late <= 7 then '4 to 7 days late'
                    else '8 or more days late' end as bucket,
               count(*) as orders,
               round(avg(review_score), 2) as avg_score,
               round(100.0 * avg(case when review_score = 1 then 1 else 0 end), 1) as one_star_pct
        from delivered join review using (order_id)
        group by 1
        order by min(days_late)
    """).fetchall()


def one_star_from_late(con):
    """Of all one star reviews, the share that came from a late order."""
    return con.execute("""
        select round(100.0 * sum(case when days_late > 0 then 1 else 0 end) / count(*), 1)
        from delivered join review using (order_id)
        where review_score = 1
    """).fetchone()[0]


def late_by_state(con, min_orders=500):
    return con.execute("""
        select customer_state as state,
               count(*) as orders,
               round(100.0 * sum(case when days_late > 0 then 1 else 0 end) / count(*), 1) as late_pct
        from delivered join customers using (customer_id)
        group by 1
        having count(*) >= ?
        order by 3 desc
    """, [min_orders]).fetchall()


def late_by_month(con, min_orders=200):
    return con.execute("""
        select strftime(ordered, '%Y-%m') as month,
               count(*) as orders,
               round(100.0 * sum(case when days_late > 0 then 1 else 0 end) / count(*), 1) as late_pct
        from delivered
        group by 1
        having count(*) >= ?
        order by 1
    """, [min_orders]).fetchall()


def top_sellers(con, min_orders=50, limit=10):
    return con.execute("""
        with seller_orders as (
            select distinct seller_id, order_id, days_late
            from order_items join delivered using (order_id)
        )
        select seller_id,
               count(*) as orders,
               sum(case when days_late > 0 then 1 else 0 end) as late,
               round(100.0 * sum(case when days_late > 0 then 1 else 0 end) / count(*), 1) as late_pct
        from seller_orders
        group by 1
        having count(*) >= ?
        order by late desc
        limit ?
    """, [min_orders, limit]).fetchall()


def late_share_of_top_sellers(con, top=20):
    """How many of all late orders come from the top sellers by late count."""
    return con.execute("""
        with seller_orders as (
            select distinct seller_id, order_id, days_late
            from order_items join delivered using (order_id)
        ),
        by_seller as (
            select seller_id, sum(case when days_late > 0 then 1 else 0 end) as late
            from seller_orders group by 1
        )
        select (select sum(late) from (select late from by_seller order by late desc limit ?)),
               (select sum(late) from by_seller)
    """, [top]).fetchone()


def late_pct_with_longer_promise(con, extra_days):
    """Late share if the promised date had been some days later."""
    return con.execute("""
        select round(100.0 * sum(case when days_late > ? then 1 else 0 end) / count(*), 1)
        from delivered
    """, [extra_days]).fetchone()[0]


def show(title, cols, rows):
    print(f"\n{title}")
    widths = [max(len(c), *(len(str(r[i])) for r in rows)) for i, c in enumerate(cols)]

    def line(values):
        return "  ".join(str(v).ljust(w) for v, w in zip(values, widths))

    print(line(cols))
    print(line(["-" * w for w in widths]))
    for r in rows:
        print(line(r))


def chart_score(rows):
    labels = [r[0] for r in rows]
    scores = [r[2] for r in rows]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    bars = ax.bar(labels, scores, color=["#2a78d6", "#c3c2b7", "#c3c2b7", "#c3c2b7"], width=0.6)
    for bar, r in zip(bars, rows):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.08, f"{r[2]:.1f}", ha="center")
        ax.text(bar.get_x() + bar.get_width() / 2, 0.15, f"{r[1]:,} orders", ha="center", color="#fff", fontsize=9)
    ax.set_ylim(0, 5)
    ax.set_ylabel("average review score")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(CHARTS / "score_by_lateness.svg")


def chart_state(rows):
    rows = list(reversed(rows))
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#2a78d6" if r[0] == "SP" else "#c3c2b7" for r in rows]
    ax.barh([r[0] for r in rows], [r[2] for r in rows], color=colors, height=0.6)
    for i, r in enumerate(rows):
        ax.text(r[2] + 0.2, i, f"{r[2]}%", va="center", fontsize=9)
    ax.set_xlabel("late deliveries, percent of orders")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(CHARTS / "late_by_state.svg")


def main():
    con = connect()
    CHARTS.mkdir(exist_ok=True)

    orders, late, late_pct = late_share(con)
    print(f"{orders:,} delivered orders, {late:,} late ({late_pct}%)")
    print(f"{one_star_from_late(con)}% of all one star reviews come from a late order")

    scores = score_by_lateness(con)
    show("Review score by lateness", ["bucket", "orders", "avg score", "one star %"], scores)
    chart_score(scores)

    show("Sellers with the most late orders (50 orders or more)",
         ["seller", "orders", "late", "late %"], [(r[0][:8], *r[1:]) for r in top_sellers(con)])
    top, total = late_share_of_top_sellers(con)
    print(f"the 20 sellers with the most late orders cause {top:,} of {total:,} late orders ({100 * top / total:.0f}%)")

    states = late_by_state(con)
    show("Late deliveries by customer state (500 orders or more)", ["state", "orders", "late %"], states)
    chart_state(states)

    show("Late deliveries by month", ["month", "orders", "late %"], late_by_month(con))

    print("\nIf the promised date had been later:")
    for days in (3, 5, 7):
        print(f"  {days} days later: {late_pct_with_longer_promise(con, days)}% late")


if __name__ == "__main__":
    main()
