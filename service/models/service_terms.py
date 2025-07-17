from django.db import models, transaction
from django.core.exceptions import ValidationError


class ServiceTerms(models.Model):
    content = models.TextField(
        default="""Online Service Booking Terms
TERMS OF BOOKING
Introduction
This business and your authorised dealer, (“Dealer”) (collectively, “We” “Our” or “Us”) offer you the option to book and pay for a service on your Vehicle (including both scheduled and non-scheduled services) online (“Booking”). Our online service booking system lets you book and pay for a service for your Vehicle with your nominated Dealer in your own space and time (“Booking System”). Placing and paying for a Booking via the Booking System is only available to Australian residents aged 18 years and over. By using the Booking System, you agree to the following terms. Before finalising your Booking via the Booking System, you must carefully read and ACCEPT these Terms and the This business Privacy Policy.
By clicking ‘CONFIRM’ and submitting payment of the Fees for your Booking, you become bound by these Terms. If you do not wish to be bound by these Terms, do not click ‘CONFIRM’ and submit payment of the Fees.
Certain laws such as the Competition and Consumer Act 2010 (Cth) and any applicable state-based consumer legislation (“Consumer Laws”) are in place for your protection. They are designed to ensure Our services are provided with due care and skill and are fit for purpose. The Terms do not alter any protection given to you under Consumer Laws.
These Terms form part of the agreement between you and the Dealer for provision of a Booking.
Definitions
In these Terms:
Additional Items means optional add-ons, services or accessory fitments in addition to your vehicle’s scheduled or non-scheduled service.
Agreement means these Terms and any document expressly referred to in them.
Booking means an online booking made by You for your Vehicle, which may include for a scheduled or non-scheduled service, accessories and/or other Additional Items, through the Booking System available via mobile applications or websites offered by the Dealer and/or This business.
Customer means a customer of this business.
Fees means the total price payable, including GST, for the confirmed Booking as displayed online (on the Booking System) or confirmed at the Dealer.
Payment Card means any valid credit card or debit card provided by you.
Personal Information has the same meaning as in the Privacy Act 1988 (Cth).
Terms means these booking and payment terms and conditions.
Vehicle means the vehicle you have made a Booking for.
Booking process
You will be guided through a step-by-step process on the Booking System that enables you to (but not limited to):
select items for Booking, including any optional Additional Items;
confirm the Booking; and
pay the Fees online
If the Booking consists of a Price on Application (“POA”) item, the Fees may not be eligible for online payment but the Booking itself may still be confirmed.
Selecting your Vehicle’s service
Pricing of the items are displayed on this business's website and as part of the Booking System.
Confirming Your Booking
Once your Booking is confirmed, you will receive an email from your preferred Dealer detailing next steps.
Management of your Booking is handled by your preferred Dealer. You acknowledge that any changes to your Booking, including but not limited to rescheduling and/or cancellation, must be made between you and the Dealer. This business is not responsible for any agreements made between you and the Dealer in relation to the management of your Booking after your Booking has been confirmed.
Payment Requirements
If you select to pay the Fees online when placing your Booking directly via the Booking System, We use a secure and encrypted online payment gateway. Payment methods may be subject to change.
If your payment is rejected, you will be invited to RETRY. If your payment is not accepted for any reason, your transaction will be cancelled by Us and you can contact the Dealer.
We reserve the right to amend any pricing errors displayed due to human error, computer malfunction or any other reason.
If your Vehicle requires unexpected work that falls outside the scope of the items included in the Booking, the Dealer will contact you to discuss. Additional items or work required on your Vehicle may have an extra cost. Any extra costs agreed between you and the Dealer are to be paid by you to the Dealer prior to collection of your Vehicle or as otherwise agreed with the Dealer.
Fulfilling your Booking
Once you deliver your Vehicle to your selected Dealer and the Booking is completed by the Dealer, your Dealer will communicate with You to confirm collection of your Vehicle, payment of the Fees and/or any additional amounts (if required), or any further arrangements.
Rescheduling or Cancelling your Booking
Rescheduling your Booking
In the event your Booking needs to be rescheduled by the Dealer for any reason, the Dealer will communicate with you in writing (including by email) or by phone as soon as reasonably practicable prior to the Booking date.
In the event you need to reschedule your Booking, you must contact the Dealer directly. This business is not responsible for any agreements made between you and the Dealer.
Cancellation by You
You may cancel your Booking at any time by notifying the Dealer in writing (including by email) or by phone prior to the Booking date.
If the Booking is cancelled by you in the prescribed time and manner, any payments made by you via the Booking System for the Booking (including the Fees) will be refunded in full and processed through our online refund system.
Cancellation by Us
The Dealer may cancel your Booking by notifying you either in writing (including by email) or by phone prior to the Booking date.
If the Booking is cancelled by the Dealer, any payments made by you via the Booking System for the Booking (including the Fees) will be refunded in full and processed through our online refund system.
Privacy
The Personal Information collected in connection with your Booking is collected by This business. The Personal Information collected by This business will be handled in accordance with This business's Privacy Policy. The terms of This business's Privacy Policy, as updated from time to time are incorporated into these Terms by reference.
Intellectual property
All information contained in this website is protected by copyright and all of the intellectual property rights in and to the Booking System belongs to This business and This business's licensors.
You are not permitted to copy, distribute, modify, create derivative works, download, store, transmit or reproduce any of the material, including but not limited to images, text or other content, from this website or the Booking System without This business's prior written consent, except as follows:
you may print or download pages of the website for your own personal, non-commercial use and not for further reproduction, publication, or distribution;
your computer may temporarily store copies of such materials in RAM incidental to your accessing and viewing those materials; and
you may store files that are automatically cached by your web browser for display enhancement purposes.
Liability
All warranties and conditions are expressly excluded from these Terms to the maximum extent permitted by law. Any liability that This business cannot by law exclude in respect of goods and services is limited, where permitted by law, to supplying, or paying the cost of supplying, the goods and services again or repairing, or paying the costs of repairing, the goods, at This business's option.
This business, the Dealer, and their officers, employees, contractors and agents will not be liable to you, your authorised representative or anyone else for any direct, indirect, incidental or consequential loss of any nature caused by, or any claim which is not attributable (directly or indirectly) to the performance, the failure to perform or the delay in performance of the obligations of This business under these Terms. In all other circumstances, liability will be limited to the maximum amount allowable by law.
General
This Agreement is governed by and must be construed in accordance with the laws in the State of Western Australia, Australia. You and This business submit to the exclusive jurisdiction of the courts of Western Australia, and courts competent to determine appeals from those courts, with respect to any proceedings that may be brought at any time relating to this Agreement and these Terms. Neither This business nor you will object to the exercise of jurisdiction of those courts on any basis.
This business may engage third parties to supply services for it in connection with the Booking System. However, the engagement of third parties under this clause will not affect This business's rights and obligations under these Terms.
Failure by either you or This business to enforce a particular term or condition does not constitute a waiver of that term or condition.
In the event of any inconsistency between these Terms and terms and conditions contained in any other material relating to the Booking System, these Terms will prevail to the extent of any inconsistency.
This business may assign or transfer its rights and obligations under these Terms to another organisation, but this will not affect your rights or This business's obligations under this Agreement or these Terms.
Contacting Us
If you have a question, problem or complaint or need to contact us for any other reason, please contact the Dealer.
"""
    )
    version_number = models.PositiveIntegerField(unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Service Terms"
        verbose_name_plural = "Service Terms"
        ordering = ["-version_number"]

    def __str__(self):
        status = "Active" if self.is_active else "Archived"
        return f"v{self.version_number} - Created: {self.created_at.strftime('%d %b %Y')} ({status})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.version_number:
            last_version = ServiceTerms.objects.all().order_by("version_number").last()
            self.version_number = (
                (last_version.version_number + 1) if last_version else 1
            )

        if self.is_active:
            with transaction.atomic():
                ServiceTerms.objects.filter(is_active=True).exclude(pk=self.pk).update(
                    is_active=False
                )

        super().save(*args, **kwargs)

    def clean(self):
        if (
            not self.is_active
            and not ServiceTerms.objects.filter(is_active=True)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(
                "You cannot deactivate the only active Service Terms version. Please activate another version first."
            )
