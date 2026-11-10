with bounds as (
    select max(stg_orders.purchase_date) as max_purchase_date
    from {{ ref('stg_orders') }} as stg_orders
)

select mart_monthly_commerce.purchase_month
from {{ ref('mart_monthly_commerce') }} as mart_monthly_commerce
cross join bounds
where last_day(mart_monthly_commerce.purchase_month) > bounds.max_purchase_date
