with delivered as (
    select
        stg_orders.order_id,
        stg_orders.purchase_month
    from {{ ref('stg_orders') }} as stg_orders
    inner join {{ ref('int_complete_months') }} as complete_months
        on stg_orders.purchase_month = complete_months.purchase_month
    where stg_orders.order_status = 'delivered'
),

item_totals as (
    select
        stg_order_items.order_id,
        sum(stg_order_items.price) as product_revenue,
        sum(stg_order_items.freight_value) as freight_revenue
    from {{ ref('stg_order_items') }} as stg_order_items
    group by stg_order_items.order_id
),

priced_orders as (
    select
        delivered.purchase_month,
        delivered.order_id,
        item_totals.product_revenue,
        item_totals.freight_revenue
    from delivered
    inner join item_totals
        on delivered.order_id = item_totals.order_id
)

select
    priced_orders.purchase_month,
    count(distinct priced_orders.order_id) as delivered_orders,
    sum(priced_orders.product_revenue) as product_revenue,
    sum(priced_orders.product_revenue + priced_orders.freight_revenue)
    / count(distinct priced_orders.order_id) as average_ticket
from priced_orders
group by priced_orders.purchase_month
