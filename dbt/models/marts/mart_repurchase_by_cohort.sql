with bounds as (
    select max(complete_months.purchase_month) as last_complete_month
    from {{ ref('int_complete_months') }} as complete_months
),

delivered as (
    select
        stg_orders.order_id,
        stg_customers.customer_unique_id,
        stg_orders.purchase_date
    from {{ ref('stg_orders') }} as stg_orders
    inner join {{ ref('stg_customers') }} as stg_customers
        on stg_orders.customer_id = stg_customers.customer_id
    where stg_orders.order_status = 'delivered'
),

per_customer as (
    select
        delivered.customer_unique_id,
        min(delivered.purchase_date) as first_purchase_date,
        count(distinct delivered.order_id) as delivered_orders
    from delivered
    group by delivered.customer_unique_id
),

mature as (
    select
        per_customer.customer_unique_id,
        per_customer.delivered_orders,
        cast(date_trunc('month', per_customer.first_purchase_date) as date) as cohort_month
    from per_customer
    cross join bounds
    where per_customer.first_purchase_date <= cast(
        last_day(bounds.last_complete_month)
        - ({{ var('repurchase_maturity_days') }} * interval 1 day) as date
    )
)

select
    mature.cohort_month,
    count(*) as mature_customers,
    count(*) filter (where mature.delivered_orders >= 2) as repurchasing_customers,
    count(*) filter (where mature.delivered_orders >= 2) * 1.0
    / count(*) as repurchase_rate_indicativo
from mature
group by mature.cohort_month
