with source_customers as (
    select
        customers.customer_id,
        customers.customer_unique_id,
        customers.customer_state
    from {{ source('olist', 'customers') }} as customers
)

select
    cast(source_customers.customer_id as varchar) as customer_id,
    cast(source_customers.customer_unique_id as varchar) as customer_unique_id,
    cast(source_customers.customer_state as varchar) as customer_state
from source_customers
where source_customers.customer_id is not null
