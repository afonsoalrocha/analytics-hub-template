select
    stg_order_items.order_id,
    stg_order_items.order_item_id
from {{ ref('stg_order_items') }} as stg_order_items
group by stg_order_items.order_id, stg_order_items.order_item_id
having count(*) > 1
