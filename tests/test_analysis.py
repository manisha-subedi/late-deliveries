from pathlib import Path

import pytest

from analysis import connect, late_share, one_star_from_late, score_by_lateness

# three delivered orders: one on time, one 2 days late, one 10 days late. one has two reviews.
ORDERS = """order_id,customer_id,order_status,order_purchase_timestamp,order_approved_at,order_delivered_carrier_date,order_delivered_customer_date,order_estimated_delivery_date
a,c1,delivered,2018-01-01 10:00:00,2018-01-01 11:00:00,2018-01-02 10:00:00,2018-01-08 10:00:00,2018-01-10 00:00:00
b,c2,delivered,2018-01-01 10:00:00,2018-01-01 11:00:00,2018-01-02 10:00:00,2018-01-12 10:00:00,2018-01-10 00:00:00
c,c3,delivered,2018-01-01 10:00:00,2018-01-01 11:00:00,2018-01-02 10:00:00,2018-01-20 10:00:00,2018-01-10 00:00:00
d,c4,canceled,2018-01-01 10:00:00,,,,2018-01-10 00:00:00
"""

REVIEWS = """review_id,order_id,review_score,review_comment_title,review_comment_message,review_creation_date,review_answer_timestamp
r1,a,5,,,2018-01-09 00:00:00,2018-01-09 10:00:00
r2,b,3,,,2018-01-13 00:00:00,2018-01-13 10:00:00
r3,c,2,,,2018-01-21 00:00:00,2018-01-21 10:00:00
r4,c,1,,,2018-01-22 00:00:00,2018-01-22 10:00:00
"""

ITEMS = """order_id,order_item_id,product_id,seller_id,shipping_limit_date,price,freight_value
a,1,p1,s1,2018-01-03 00:00:00,10.0,2.0
b,1,p1,s1,2018-01-03 00:00:00,10.0,2.0
c,1,p2,s2,2018-01-03 00:00:00,20.0,3.0
"""

CUSTOMERS = """customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state
c1,u1,1000,sao paulo,SP
c2,u2,2000,rio,RJ
c3,u3,3000,salvador,BA
c4,u4,4000,sao paulo,SP
"""


@pytest.fixture
def con(tmp_path):
    for name, text in [("orders", ORDERS), ("order_reviews", REVIEWS), ("order_items", ITEMS), ("customers", CUSTOMERS)]:
        (tmp_path / f"olist_{name}_dataset.csv").write_text(text)
    return connect(tmp_path)


def test_only_delivered_orders_count(con):
    assert late_share(con) == (3, 2, 66.7)


def test_buckets_and_newest_review(con):
    rows = score_by_lateness(con)
    assert [r[0] for r in rows] == ["on time", "1 to 3 days late", "8 or more days late"]
    assert rows[2][2] == 1.0  # order c has two reviews, the newest one is 1 star


def test_one_star_share(con):
    assert one_star_from_late(con) == 100.0
