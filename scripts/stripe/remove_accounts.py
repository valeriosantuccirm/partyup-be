import os

import stripe

STRIPE_SECRET_API_KEY: str = os.environ["STRIPE_SECRET_API_KEY"]


def main() -> None:
    try:
        accounts: stripe.ListObject[stripe.Account] = stripe.Account.list(
            api_key=STRIPE_SECRET_API_KEY
        )
        removable = ("acct_1Sv2QhK5uGfNoXLz",)
        for r in removable:
            stripe.Account.delete(
                r,
                api_key=STRIPE_SECRET_API_KEY,
            )
    except Exception as e:
        raise e


if __name__ == "__main__":
    main()
