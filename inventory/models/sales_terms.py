from django.db import models, transaction
from django.core.exceptions import ValidationError

DEFAULT_SALES_TERMS_CONTENT = """Website and Online Sales Terms & Conditions
1. General Website Terms
This site is provided as an introduction to this business only, based on general information including that provided by third parties. Information given may change and some time may pass before this website can be updated in respect of all information affected. That being so, this business does not guarantee or warrant that information on this website is accurate or complete and makes no representations or warranties of any kind, express or implied, as to the operation of the site or the information, content or details disclosed on this site.
Except as expressly provided for in writing or as regarded by law, the liability of this business arising from the use of this site or the goods and services purchased using this site is specifically excluded and this business disclaims all warranties and any liability for damages of any kind and any liability whether in contract, tort under statute or otherwise for any injury, damage or loss whatsoever. No reliance should be placed on information contained or is to be implied or inferred from this website without checking the details with an authorised officer of this business. Specifications and descriptions are provided by manufacturers.

Vehicle Information
The information, pictures, colours, and specifications contained within the this business website are presented as a general guide only. Although every effort has been made to ensure that such information is correct and up to date, no warrant is provided that all such information is reliable, complete, accurate or without error. In some cases, pictures of overseas models may be shown as a guide. Therefore, this business does not accept liability for damages of any kind resulting from the access or use of this site and its contents. All vehicles are subject to prior sale. You must contact us to confirm the availability and details of any vehicle.

2. Online Vehicle Reservation & Sales Terms
Introduction
This business (collectively, “We”, “Our”, or “Us”) offers you the option to submit an enquiry, request a viewing, and/or reserve a Vehicle by paying a deposit online (“Reservation”). Our online system allows you to initiate the purchase process for your chosen Vehicle in your own space and time (“Reservation System”).
Placing a Reservation via the Reservation System is only available to Australian residents aged 18 years and over. By using the Reservation System, you agree to the following terms. Before finalising your Reservation, you must carefully read and ACCEPT these Terms and the this business Privacy Policy.
By clicking ‘CONFIRM’ and submitting your details and/or payment of the Deposit for your Reservation, you become bound by these Terms. If you do not wish to be bound by these Terms, do not proceed with the Reservation.
Certain laws such as the Competition and Consumer Act 2010 (Cth) and any applicable state-based consumer legislation (“Consumer Laws”) are in place for your protection. They are designed to ensure Our services are provided with due care and skill and are fit for purpose. These Terms do not alter any protection given to you under Consumer Laws.

Definitions
In these Terms:

Agreement means these Terms and any document expressly referred to in them.
Reservation means an online reservation made by You for a specific Vehicle, which may include requesting a viewing appointment and/or paying a Deposit to secure the Vehicle.
Customer means a customer of this business.
Deposit means the amount payable, including GST, to secure the Reservation of a Vehicle as displayed online.
Final Purchase Price means the total advertised price of the Vehicle, including any government duties, fees, and taxes, less any Deposit paid.
Payment Card means any valid credit card or debit card provided by you.
Personal Information has the same meaning as in the Privacy Act 1988 (Cth).
Terms means these reservation and sales terms and conditions.
Vehicle means the specific new or used vehicle you have made a Reservation for.
Reservation Process
You will be guided through a step-by-step process on the Reservation System that enables you to:

Select a Vehicle.
Provide your personal and contact information.
Optionally, request a viewing appointment with us.
Accept these Terms and Conditions.
Pay the required Deposit to reserve the Vehicle from being sold to another party.
Once your Reservation is confirmed and your Deposit is successfully paid, the selected Vehicle will be placed in a "reserved" status and will not be available for other customers to purchase online.

Confirming Your Reservation
Once your Reservation is confirmed, you will receive an email from us detailing your Reservation and the next steps to complete the purchase.
Management of your vehicle purchase is handled by us. You acknowledge that all further steps, including but not limited to finalising finance, arranging a trade-in, completing sale contracts, and arranging final payment and collection, must be made between you and us.

Deposit and Payment Requirements
If you select to pay the Deposit online, We use a secure and encrypted online payment gateway.

The Deposit secures the Vehicle for a period agreed upon with us, preventing its sale to another party.
The Deposit is applied towards the Final Purchase Price of the Vehicle.
The remaining balance of the Final Purchase Price is payable directly to us prior to the collection of your Vehicle, or as per the terms of your sale contract.
If your Deposit payment is rejected, your transaction will be cancelled, and the Vehicle will remain available for sale.
If your Vehicle requires any additional accessories or work that falls outside the advertised package, we will contact you to discuss. Any extra costs agreed between you and us are to be paid by you to us.

Fulfilling your Reservation (Completing the Sale)
We will contact you within a reasonable timeframe after your Reservation is confirmed to arrange the next steps. This may include:

Confirming your viewing appointment (if requested).
Finalising the contract of sale.
Discussing trade-in and finance options.
Arranging final payment and a time for you to take delivery of your Vehicle.
Rescheduling or Cancelling your Reservation
Rescheduling a Viewing Appointment
In the event you need to reschedule your viewing appointment, you must contact us directly.
Cancellation by You You may cancel your Reservation at any time by notifying us in writing (including by email).

If you cancel the Reservation or decide not to proceed with the purchase for any reason, the Deposit is non-refundable and will be forfeited to us to cover administrative and other costs incurred in holding the vehicle for you.
Cancellation by Us
We may cancel your Reservation by notifying you in writing (including by email) or by phone prior to the completion of the sale contract. This may occur if the vehicle is found to be damaged, stolen, or otherwise unable to be sold.

If the Reservation is cancelled by us, any Deposit paid by you will be refunded in full. The refund will be processed through our online refund system to the original Payment Card used.
3. Privacy, Intellectual Property & Liability
Privacy
The Personal Information collected in connection with your Reservation is collected by this business. The Personal Information collected by this business will be handled in accordance with this business's Privacy Policy. The terms of this business's Privacy Policy, as updated from time to time, are incorporated into these Terms by reference.

Intellectual Property
All information contained in this website is protected by copyright and all of the intellectual property rights in and to the Reservation System belongs to this business and this business's licensors. You are not permitted to copy, distribute, modify, create derivative works, download, store, transmit or reproduce any of the material from this website or the Reservation System without this business's prior written consent.

Liability
To the maximum extent permitted by law, all warranties and conditions are expressly excluded from these Terms. Any liability that this business cannot by law exclude in respect of goods and services is limited, where permitted by law, to supplying, or paying the cost of supplying, the goods and services again or repairing, or paying the costs of repairing, the goods, at this business's option.
This business and its officers, employees, contractors and agents will not be liable to you, your authorised representative or anyone else for any direct, indirect, incidental or consequential loss of any nature caused by, or any claim which is not attributable (directly or indirectly) to the performance, the failure to perform or the delay in performance of the obligations of this business under these Terms.

4. General
This Agreement is governed by and must be construed in accordance with the laws in the State of Western Australia, Australia. You and this business submit to the exclusive jurisdiction of the courts of Western Australia.
This business may assign or transfer its rights and obligations under these Terms to another organisation, but this will not affect your rights or this business's obligations under this Agreement or these Terms.

Contacting Us
If you have a question, problem or complaint or need to contact us for any other reason in relation to your online Reservation or vehicle purchase, please contact us directly."""

class SalesTerms(models.Model):
    content = models.TextField(
        default=DEFAULT_SALES_TERMS_CONTENT
    )
    version_number = models.PositiveIntegerField(
        unique=True,
        blank=True
    )
    is_active = models.BooleanField(
        default=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Terms and Conditions"
        verbose_name_plural = "Terms and Conditions"
        ordering = ['-version_number']

    def __str__(self):
        status = 'Active' if self.is_active else 'Archived'
        return f"v{self.version_number} - Created: {self.created_at.strftime('%d %b %Y')} ({status})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.version_number:
            last_version = SalesTerms.objects.all().order_by('version_number').last()
            self.version_number = (last_version.version_number + 1) if last_version else 1

        if self.is_active:
            with transaction.atomic():
                SalesTerms.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        
        super().save(*args, **kwargs)

    def clean(self):
        if not self.is_active and not SalesTerms.objects.filter(is_active=True).exclude(pk=self.pk).exists():
             raise ValidationError("You cannot deactivate the only active Terms and Conditions version. Please activate another version first.")
