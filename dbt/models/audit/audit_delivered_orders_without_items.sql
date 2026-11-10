with delivered as (
    select
        stg_orders.order_id,
        stg_orders.purchase_month
    from {{ ref('stg_orders') }} as stg_orders
    inner join {{ ref('int_complete_months') }} as complete_months
        on stg_orders.purchase_month = complete_months.purchase_month
    where stg_orders.order_status = 'delivered'
),

item_orders as (
    select distinct stg_order_items.order_id
    from {{ ref('stg_order_items') }} as stg_order_items
)

select
    delivered.order_id,
    delivered.purchase_month
from delivered
left join item_orders
    on delivered.order_id = item_orders.order_id
where item_orders.order_id is null
