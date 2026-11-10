with source_items as (
    select
        order_items.order_id,
        order_items.order_item_id,
        order_items.product_id,
        order_items.seller_id,
        order_items.shipping_limit_date,
        order_items.price,
        order_items.freight_value
    from {{ source('olist', 'order_items') }} as order_items
)

select
    cast(source_items.order_id as varchar) as order_id,
    cast(source_items.order_item_id as integer) as order_item_id,
    cast(source_items.product_id as varchar) as product_id,
    cast(source_items.seller_id as varchar) as seller_id,
    cast(source_items.shipping_limit_date as timestamp) as shipping_limit_date,
    cast(source_items.price as double) as price,
    cast(source_items.freight_value as double) as freight_value
from source_items
where source_items.order_id is not null
