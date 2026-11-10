with source_orders as (
    select
        orders.order_id,
        orders.customer_id,
        orders.order_status,
        orders.order_purchase_timestamp,
        orders.order_approved_at,
        orders.order_delivered_carrier_date,
        orders.order_delivered_customer_date,
        orders.order_estimated_delivery_date
    from {{ source('olist', 'orders') }} as orders
),

typed as (
    select
        cast(source_orders.order_id as varchar) as order_id,
        cast(source_orders.customer_id as varchar) as customer_id,
        cast(source_orders.order_status as varchar) as order_status,
        cast(source_orders.order_purchase_timestamp as timestamp) as order_purchase_timestamp,
        cast(source_orders.order_approved_at as timestamp) as order_approved_at,
        cast(source_orders.order_delivered_carrier_date as timestamp)
            as order_delivered_carrier_date,
        cast(source_orders.order_delivered_customer_date as timestamp)
            as order_delivered_customer_date,
        cast(source_orders.order_estimated_delivery_date as timestamp)
            as order_estimated_delivery_date,
        cast(source_orders.order_purchase_timestamp as date) as purchase_date,
        cast(date_trunc('month', source_orders.order_purchase_timestamp) as date) as purchase_month
    from source_orders
)

select
    typed.order_id,
    typed.customer_id,
    typed.order_status,
    typed.order_purchase_timestamp,
    typed.order_approved_at,
    typed.order_delivered_carrier_date,
    typed.order_delivered_customer_date,
    typed.order_estimated_delivery_date,
    typed.purchase_date,
    typed.purchase_month
from typed
where typed.order_id is not null
