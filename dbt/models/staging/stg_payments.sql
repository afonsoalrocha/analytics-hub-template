with source_payments as (
    select
        payments.order_id,
        payments.payment_sequential,
        payments.payment_type,
        payments.payment_installments,
        payments.payment_value
    from {{ source('olist', 'payments') }} as payments
)

select
    cast(source_payments.order_id as varchar) as order_id,
    cast(source_payments.payment_sequential as integer) as payment_sequential,
    cast(source_payments.payment_type as varchar) as payment_type,
    cast(source_payments.payment_installments as integer) as payment_installments,
    cast(source_payments.payment_value as double) as payment_value
from source_payments
where source_payments.order_id is not null
