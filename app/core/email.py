from fastapi import Request
from fastapi_mail import FastMail, MessageSchema, MessageType
from firebase_admin import auth
from jinja2.environment import Template

from app.config import emailconfig, emailenv


class Email:
    """
    A class to handle sending emails to a user.

    This class provides methods to send various types of emails, including
    verification emails and password reset links, using predefined templates.

    Args:
        request (Request): The HTTP request object, typically used for user-specific information.
        user_email (str): The email address of the user to whom the email will be sent.
    """

    def __init__(
        self,
        request: Request,
        user_email: str,
    ) -> None:
        self.user_email: str = user_email
        self.request: Request = request

    async def send_email(self, subject: str, template_name: str, url: str) -> None:
        """
        Sends an email using a specified template.

        This method renders the HTML template based on the provided template filename,
        replaces the placeholders with dynamic content, and sends the email to the user.

        Args:
            subject (str): The subject of the email.
            template_name (str): The name of the HTML email template to use.
            url (str): The URL to include in the email body (e.g., verification or action link).
        """
        # Generate the HTML template based on the template name
        template: Template = emailenv.get_template(name=f"{template_name}.html")
        html: str = template.render(
            url=url,
            first_name=self.user_email,
            subject=subject,
        )
        # Create email message
        message = MessageSchema(
            subject=subject,
            recipients=[self.user_email],
            body=html,
            subtype=MessageType.html,
        )
        # Send the email
        fm = FastMail(config=emailconfig)
        await fm.send_message(message=message)

    async def send_verification_email(self) -> None:
        """
        Sends a Firebase email verification link.

        This method generates a Firebase email verification link for the user's email address
        and sends it using the `send_email` method with the appropriate template.
        """
        # Generate Firebase email verification link
        verification_link: str = auth.generate_email_verification_link(
            email=self.user_email
        )

        # Send email with the verification link
        await self.send_email(
            subject="PartyUp Email Verification",
            template_name="verification",
            url=verification_link,
        )

    async def send_reset_password_link(self) -> None:
        """
        Sends a Firebase reset password link.

        This method generates a Firebase reset password link for the user's email address
        and sends it using the `send_email` method with the appropriate template.
        """
        # Generate Firebase email verification link
        reset_pswd_link: str = auth.generate_password_reset_link(email=self.user_email)

        # Send email with the verification link
        await self.send_email(
            subject="PartyUp Account Reset Password",
            template_name="reset_pswd",
            url=reset_pswd_link,
        )
