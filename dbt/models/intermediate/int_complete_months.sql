with source_days as (
    select distinct stg_orders.purchase_date
    from {{ ref('stg_orders') }} as stg_orders
    where stg_orders.purchase_date is not null
),

bounds as (
    select max(source_days.purchase_date) as max_purchase_date
    from source_days
),

months as (
    select
        cast(date_trunc('month', source_days.purchase_date) as date) as purchase_month,
        count(distinct source_days.purchase_date) as days_with_orders
    from source_days
    group by cast(date_trunc('month', source_days.purchase_date) as date)
)

select months.purchase_month
from months
cross join bounds
where
    months.days_with_orders
    = date_diff('day', months.purchase_month, last_day(months.purchase_month)) + 1
    and last_day(months.purchase_month) <= bounds.max_purchase_date
