import json
import os
from datetime import datetime
from typing import Optional

import stripe
import uvicorn
from pydantic import BaseModel
from fastapi import HTTPException, FastAPI, Response, Depends, Header, Request
from uuid import UUID, uuid4
from fastapi_sessions.backends.implementations import InMemoryBackend
from fastapi_sessions.session_verifier import SessionVerifier
from fastapi_sessions.frontends.implementations import SessionCookie, CookieParameters
from starlette.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles


class SessionData(BaseModel):
    api_key: str


stripe.api_key =  'sk_test_<>'
endpoint_secret = 'whsec_<>'
stripe_item_1 = 'prod_<>'
stripe_item_1_price = 'price_<>'

cookie_params = CookieParameters()
stripe_customer = None

webhook_log: list[str] = []


# Uses UUID
cookie = SessionCookie(
    cookie_name="cookie",
    identifier="general_verifier",
    auto_error=True,
    secret_key="DONOTUSE",
    cookie_params=cookie_params,
)
backend = InMemoryBackend[UUID, SessionData]()


class BasicVerifier(SessionVerifier[UUID, SessionData]):
    def __init__(
            self,
            *,
            identifier: str,
            auto_error: bool,
            backend: InMemoryBackend[UUID, SessionData],
            auth_http_exception: HTTPException,
    ):
        self._identifier = identifier
        self._auto_error = auto_error
        self._backend = backend
        self._auth_http_exception = auth_http_exception

    @property
    def identifier(self):
        return self._identifier

    @property
    def backend(self):
        return self._backend

    @property
    def auto_error(self):
        return self._auto_error

    @property
    def auth_http_exception(self):
        return self._auth_http_exception

    def verify_session(self, model: SessionData) -> bool:
        """If the session exists, it is valid"""
        return True


verifier = BasicVerifier(
    identifier="general_verifier",
    auto_error=True,
    backend=backend,
    auth_http_exception=HTTPException(status_code=403, detail="invalid session"),
)

app = FastAPI()


@app.get('/create-checkout-session', response_class=RedirectResponse, status_code=303)
def create_checkout_session(api_key, customer_data=None, list_items=None):
    """
    This method is routed to during the purchase session. 
    """

    global endpoint_secret
    # could be retrieved from the session object or registration
    #  page of the web store if customer is logged in or begins registration
    # customer_data = None

    if not stripe.api_key or not endpoint_secret:
        return 'static/error_session.html'

    # data form web store shopping-cart (could be retrieved from DB)
    list_items = [
        {
            'price': stripe_item_1_price,
            'quantity': 1
        }
    ]

    # filled out based on info if customer is authenticated on the web site and already has payment information registered in the DB. 
    session = stripe.checkout.Session.create(
        payment_intent_data={
            'setup_future_usage': 'off_session',
        },
        payment_method_types=['card'],
        line_items=list_items,
        mode='payment',
        success_url='https://stripe-demo-jx-production.cl1.ahb.dev/static/success.html',
        cancel_url='https://stripe-demo-jx-production.cl1.ahb.dev/static/cancel.html',
        api_key=api_key
    )

    return session.url


@app.post('/webhook')
async def webhook(request: Request):
    """
    Captures events from Stripe Session
    """
    global webhook_log, stripe_customer, endpoint_secret
    event = None

    payload = await request.body()

    sig_header = request.headers['stripe-signature']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        raise e
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise e

    webhook_log.append(f'{str(datetime.now())}:     {event["type"]}')

    # Handle the event
    if event['type'] == 'customer.created' and stripe_customer != event['data']['object']['id']:
        stripe_customer = event['data']['object']['id']

        # save customer to db here [MARK AS NEW CUSTOMER]
        # db op here

        webhook_log.append(f'{str(datetime.now())}:     {event["type"]}')


    elif event['type'] == 'payment_method.attached':
        payment_method = event['data']['object']

        # stripe_customer = customer_id  # get customer from DB
        if stripe_customer:
            payment_method = event['data']['object']

            # sets the customer default payment
            try:
                stripe.Customer.modify(
                    stripe_customer,  # customer id
                    invoice_settings={'default_payment_method': payment_method['id']}
                )
            except Exception as e: #race condition
                try:
                    stripe.PaymentMethod.attach(
                        payment_method['id'],
                        customer=stripe_customer
                    )
                except Exception as e2:  #race condition:
                    pass

                stripe.Customer.modify(
                    stripe_customer,  # customer id
                    invoice_settings={'default_payment_method': payment_method['id']}
                )
        webhook_log.append(f'{str(datetime.now())}:     {event["type"]}')

        pass


    return {'success': True}


@app.get('/')
def get_root():
    response = 'Server works!'
    return response


@app.get('/{customer_id}/list-invoices', dependencies=[Depends(cookie)])
def get_invoices(customer_id=None, session_data: SessionData = Depends(verifier)):
    invoices = stripe.Invoice.list(
        customer=customer_id,
        api_key=session_data.api_key
    )

    return invoices


@app.get('/invoice/{invoice_id}', dependencies=[Depends(cookie)])
def get_invoice(invoice_id, session_data: SessionData = Depends(verifier)):
    invoice = stripe.Invoice.retrieve(
        invoice_id,
        api_key=session_data.api_key
    )
    return invoice


@app.get('/{customer_id}/list-payment-methods', dependencies=[Depends(cookie)])
def list_payment_methods(customer_id=None, session_data: SessionData = Depends(verifier)):
    payment_methods = stripe.PaymentMethod.list(
        customer=customer_id,
        type="card",
        api_key=session_data.api_key
    )

    return payment_methods


@app.delete('/{payment_method_id}', dependencies=[Depends(cookie)])
def delete_payment_method(payment_method_id, session_data: SessionData = Depends(verifier)):
    stripe.PaymentMethod.detach(
        payment_method_id,
        api_key=session_data.api_key
    )


@app.post('/{customer_id}/add-payment-method/{stripe_payment_method_id}', dependencies=[Depends(cookie)])
def add_payment_method(customer_id, stripe_payment_method_id, session_data: SessionData = Depends(verifier)):
    """
    UI will collect payment information and send it to Stripe. In return it will get a token pm_*****
    """
    payment_method = stripe.PaymentMethod.attach(
        stripe_payment_method_id,
        customer=customer_id,
        api_key=session_data.api_key
    )

    # store id in DB.

    return payment_method


@app.get('/{customer_id}/renew-purchase', dependencies=[Depends(cookie)])
def renew_purchase(customer_id, items=[], session_data: SessionData = Depends(verifier)):
    """
    Connects to the and sets the state of the items 
    """

    customer = ''  # 'Customer info retrieved from DB.'

    items = [
        stripe_item_1,
        stripe_item_1,
        stripe_item_1,
    ]

    for bag in items:
        price = stripe.Price.create(
            product=bag,
            unit_amount=1099,
            currency='usd',
            api_key=session_data.api_key
        )

        stripe.InvoiceItem.create(
            customer=customer_id,
            price=price['id'],
            api_key=session_data.api_key
        )

    invoice = stripe.Invoice.create(
        customer=customer_id,
        auto_advance=True,  # auto-finalize this draft after ~1 hour
        api_key=session_data.api_key
    )

    stripe.api_key = session_data.api_key
    # if customer has Auto-Collect turned on, then collect (perhaps auto-collect PLUS stripe feature?)
    invoice = stripe.Invoice.finalize_invoice(invoice['id'], api_key=session_data.api_key)
    invoice = stripe.Invoice.pay(invoice)


    return invoice


@app.post("/set-demo-customer")
async def set_demo_customer(customer_id):
    global stripe_customer
    stripe_customer = customer_id


@app.post("/unset-demo-customer")
async def unset_demo_customer():
    global stripe_customer
    stripe_customer = None


@app.post("/get-demo-customer")
async def get_demo_customer():
    global stripe_customer
    return stripe_customer


@app.get('/get-webhook-log')
def get_webhook_log():
    global webhook_log
    return webhook_log


@app.post('/clear-webhook-log')
def clear_webhook_log():
    global webhook_log
    webhook_log = []


@app.post("/create_session")
async def create_session(api_key: str, webhook_key, response: Response):
    global endpoint_secret
    session = uuid4()
    data = SessionData(api_key=api_key, webhook_key=webhook_key)
    endpoint_secret=webhook_key
    webhook_log = []

    await backend.create(session, data)
    cookie.attach_to_response(response, session)
    stripe.api_key = api_key

    return f"created session for {api_key}"


@app.get("/whoami", dependencies=[Depends(cookie)])
async def whoami(session_data: SessionData = Depends(verifier)):
    return session_data


@app.post("/delete_session")
async def del_session(response: Response, session_id: UUID = Depends(cookie)):
    await backend.delete(session_id)
    cookie.delete_from_response(response)
    stripe.api_key = None
    webhook_log = []

    endpoint_secret = None
    return "deleted session"


import pathlib

_dir = pathlib.Path().resolve()

app.mount("/static", StaticFiles(directory=f"{_dir}/static"), name="static")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host='0.0.0.0',
        reload=True,
        port=8080,
        debug=False
    )
