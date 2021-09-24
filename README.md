# Stripe Integration Using FastAPI

## Implementation with the following examples:

### Checkout Sessions
- https://stripe.com/docs/api/checkout/sessions
- https://stripe.com/docs/payments/integration-builder
- https://stripe.com/docs/payments/accept-a-payment-synchronously

### Customer and Payment Methods
- https://stripe.com/docs/api/customers
- https://stripe.com/docs/api/payment_methods

### Invoicing
- https://stripe.com/docs/api/invoices
- https://stripe.com/docs/invoicing/integration
- https://stripe.com/docs/payments/save-during-payment#web-submit-payment

### Additional topics
- https://stripe.com/docs/invoicing/automatic-collection#settings
- https://stripe.com/docs/tax/checkout

### Webhooks
- https://dashboard.stripe.com/test/webhooks/create?endpoint_location=local
- https://stripe.com/docs/payments/checkout/fulfill-orders

  *Use `stripe listen --forward-to localhost:8080/webhook` to get webhooks running with the Stripe Admin CLI*


**NOTE: This uses cookie sec with in-memory. This should not be security on your app. This was done for a demo running on local host. Look into securing your server through other means This is a good start: https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/**

![image](https://user-images.githubusercontent.com/25950773/134627022-978c3b5b-7707-4836-8370-589dc7712a3c.png)

