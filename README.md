# Late deliveries and bad reviews

Late deliveries are 7 percent of orders and 37 percent of one star reviews.
The problem is not the sellers. It is the promised date, in some states and
in some months.

Data: Olist, a Brazilian online marketplace. About 100,000 orders from 2016
to 2018, with the promised delivery date, the real delivery date, and the
customer's review. Free on Kaggle:
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
The license is CC BY-NC-SA 4.0, so the data is not in this repo.

## The question

When a parcel arrives late, how much does the review drop? And where do the
late orders come from?

## What I found

**1. Late is rare, but it hurts a lot.** 96,470 delivered orders, 6,534
late, 6.8 percent. On-time orders get 4.3 stars on average. One to three
days late: 3.3 stars. Four to seven days: 2.1. Eight days or more: 1.7, and
seven of ten of those orders get one star.

![Average review score by lateness](charts/score_by_lateness.svg)

**2. Late orders make 37 percent of all one star reviews.** If the shop
wants fewer one star reviews, late delivery is the first place to look.

**3. It is not a few bad sellers.** The 20 sellers with the most late orders
cause 25 percent of them, and their late rate is 5 to 10 percent, close to
everyone else. There is no seller to fire.

**4. It is where the parcel goes.** São Paulo, the biggest state, is 4.5
percent late. Rio de Janeiro is 12 percent. Bahia 12, Ceará 14, Maranhão 17.
These four states are 18 percent of orders and 34 percent of late orders.
The promise is the same everywhere. The roads are not.

![Late deliveries by customer state](charts/late_by_state.svg)

**5. And when.** Most months are 3 to 6 percent late. November 2017, Black
Friday, was 12 percent. February and March 2018 were 14 and 19 percent.

## What I would do

The promised date is the one thing the shop controls. Two changes:

- **Promise more days for Rio and the northeast.** If every promise had been
  3 days later, the late share drops from 6.8 to 4.8 percent. 7 days later,
  3.0 percent. A longer promise costs little: on-time orders that took 22
  days or more still get 3.9 stars. A broken promise costs two stars.
- **Add buffer days in November, February, and March.** The same promise
  does not work in the busy months.

Both changes need no new trucks. They change a number on the checkout page.

## How the numbers were made

- Only delivered orders with a delivery date: 96,470.
- Late means the delivery date is after the promised date, in calendar days.
- A few orders have two reviews. I keep the newest one.
- An order with items from two sellers counts for both sellers.
- States with at least 500 orders, months with at least 200, sellers with at least 50.

All of it is in `analysis.py`, about 150 lines of SQL and Python on DuckDB.

## Run it

```bash
uv venv && uv pip install -e ".[dev]"
# put the Kaggle csv files in data/
python analysis.py
pytest
```

`analysis.py` prints every table above and writes the two charts to
`charts/`. The tests run the same queries on four made-up orders.
