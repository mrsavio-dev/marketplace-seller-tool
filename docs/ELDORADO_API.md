# Eldorado Seller API: what it does and what it does not

Source: Eldorado's help article "How the seller API works"
(https://support.eldorado.gg/en/articles/16127288-how-the-seller-api-works, read 2026-11-27).

## Access

- Only verified sellers. Maximum **2 active credentials** per account.
- Credentials are generated at Dashboard > Seller API: a credential name, an expiration period
  (1, 14, 30, 90 or 365 days), then a **Client ID** and **Client secret**. The secret is shown once.
- **There is no test environment.** Every request changes live offers and orders. Try a single
  offer first.

## Authentication

1. `POST https://eldorado.gg/api/authentication/seller/token` with the Client ID and Client secret.
2. Send the returned token in the `Authorization` header of every request.
3. Tokens expire after **15 minutes**; request a new one.

This repository implements exactly that (`src/marketplace_tool/api.py`) and `check-auth` proves it
works without touching an offer.

## Covered by the API

- Offers: create, update, pause, resume, delete across currency, top-ups, items, accounts and boosting.
- Change price, quantity and delivery time for one offer or a whole game; bulk CSV upload.
- Orders: view, mark delivered, cancel, fix delivery details, generate an invoice.
- Account: go online/offline, read notifications, check restrictions.

## Not covered by the API

- Withdrawals and balance.
- **Messages, disputes and feedback.** This is why "auto-reply to buyers" cannot be built on the
  Seller API. It would need the website itself or another channel.
- Account settings, verification, offer limit requests.
- Offer images and sales reports.

## Open questions to confirm with api@eldorado.gg

1. The exact paths and payloads for listing your own offers and updating an offer's price.
2. Whether any endpoint returns **competing offers** for a product (needed for repricing without
   reading the public site).
3. Rate limits, and whether a price update endpoint exists that is cheaper than a full offer update.

Until 1 and 2 are answered, this project runs in dry-run with a JSON competitor file and refuses
live mode (`endpoints_verified: false`).
