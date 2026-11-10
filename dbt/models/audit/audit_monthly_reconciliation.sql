with delivered as (
    select
        stg_orders.order_id,
        stg_orders.purchase_month
    from {{ ref('stg_orders') }} as stg_orders
    inner join {{ ref('int_complete_months') }} as complete_months
        on stg_orders.purchase_month = complete_months.purchase_month
    where stg_orders.order_status = 'delivered'
),

items as (
    select
        stg_order_items.order_id,
        sum(stg_order_items.price) as product_revenue,
        sum(stg_order_items.freight_value) as freight_revenue
    from {{ ref('stg_order_items') }} as stg_order_items
    group by stg_order_items.order_id
),

payments as (
    select
        stg_payments.order_id,
        sum(stg_payments.payment_value) as payment_value
    from {{ ref('stg_payments') }} as stg_payments
    group by stg_payments.order_id
)

select
    delivered.purchase_month,
    sum(items.product_revenue) as product_revenue,
    sum(items.freight_revenue) as freight_revenue,
    sum(items.product_revenue + items.freight_revenue) as item_gmv,
    sum(payments.payment_value) as payment_gmv
from delivered
inner join items
    on delivered.order_id = items.order_id
left join payments
    on delivered.order_id = payments.order_id
group by delivered.purchase_month
