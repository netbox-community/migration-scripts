from dcim.models import Site
from extras.scripts import BooleanVar, ChoiceVar, ObjectVar, Script
from ipam.models import ASN, RIR
from tenancy.choices import ContactPriorityChoices
from tenancy.models import Contact, ContactAssignment, ContactRole

name = "NetBox v3.2 Migration"


class MigrateSiteContactsScript(Script):
    """
    This script looks for Sites with a contact_name defined and attempts to create new Contact instances from the
    associated contact data. A new Contact will be created for each *unique* set of name, phone, and email values.
    Contacts for which an assignment already exists will be skipped.

    While suitable for many use cases, the author is encouraged to modify this script to better suit his or her
    own environment as needed.
    """
    contact_role = ObjectVar(
        model=ContactRole,
        description="The role to apply when assigning contacts to sites"
    )
    contact_priority = ChoiceVar(
        choices=ContactPriorityChoices,
        required=False,
        description="The priority to apply when assigning contacts to sites"
    )
    clear_site_fields = BooleanVar(
        required=False,
        description="Clear legacy site contact values after creating a new contact assignment"
    )

    class Meta:
        name = "Migrate site contacts"
        description = "Create new contact objects from legacy site contact fields"
        commit_default = False

    @staticmethod
    def _get_contact_data(site):
        name = site.contact_name.strip()
        phone = site.contact_phone.strip()
        email = site.contact_email.strip()

        # Return only fields which have a value after sanitization
        attrs = {
            'name': name
        }
        if phone:
            attrs['phone'] = phone
        if email:
            attrs['email'] = email

        return attrs

    def run(self, data, commit):

        contacts_created = 0
        assignments_created = 0

        # Retrieve all Sites with contact_name defined
        sites = Site.objects.exclude(contact_name='')
        if not sites:
            self.log_warning(f"No sites found with legacy contact information defined; aborting.")
            return
        self.log_info(f"Found {sites.count()} sites with legacy contact information defined.")

        for site in sites:

            # Extract the contact attributes from the Site
            contact_data = self._get_contact_data(site)
            contact = Contact.objects.filter(**contact_data).first()

            # Create a new Contact if this combination of attributes is new
            if not contact:
                self.log_success(f"Creating new contact: {contact_data['name']}")
                contact = Contact(**contact_data)
                contact.save()
                contacts_created += 1

            # Check whether a ContactAssignment already exists for this Site and Contact
            elif site.contacts.filter(contact=contact).exists():
                self.log_info(f"Skipping contact {contact} for site {site}; assignment already exists")
                continue

            # Assign the Contact to the Site
            self.log_success(f"Assigning contact {contact} to site {site}")
            assignment = ContactAssignment(
                object=site,
                contact=contact,
                role=data['contact_role'],
                priority=data['contact_priority']
            )
            assignment.save()
            assignments_created += 1

            # Clear legacy contact fields on Site (if enabled)
            if data['clear_site_fields']:
                self.log_debug(f"Clearing legacy contact data for site {site}")
                Site.objects.filter(pk=site.pk).update(
                    contact_name='',
                    contact_phone='',
                    contact_email=''
                )

        self.log_success(f"Created {contacts_created} contacts")
        self.log_success(f"Created {assignments_created} contact assignments")


class MigrateSiteASNsScript(Script):
    """
    This script looks for Sites which have a legacy ASN set, and creates or assigns an ASN object in its place.

    While suitable for many use cases, the author is encouraged to modify this script to better suit his or her
    own environment as needed.
    """
    asn_rir = ObjectVar(
        model=RIR,
        description="RIR to assign to newly created ASNs",
        label='RIR'
    )
    clear_site_field = BooleanVar(
        required=False,
        description="Clear legacy site ASN field after migration"
    )

    class Meta:
        name = "Migrate site ASNs"
        description = "Create/assign ASN objects from legacy site ASN fields"
        commit_default = False

    def run(self, data, commit):

        asns_created = 0
        asns_assigned = 0

        # Find all Sites with a legacy ASN value assigned
        sites = Site.objects.filter(asn__isnull=False)
        if not sites:
            self.log_warning(f"No sites found with a legacy ASN defined; aborting.")
            return
        self.log_info(f"Found {sites.count()} sites with a legacy ASN defined.")

        for site in sites:

            asn = ASN.objects.filter(asn=site.asn).first()

            # Create a new ASN object if this AS number is new
            if not asn:
                self.log_success(f"Creating new ASN: {site.asn}")
                asn = ASN(asn=site.asn, rir=data['asn_rir'])
                asn.save()
                asns_created += 1

            # Check whether this ASN has already been assigned to this Site (via the many-to-many relationship)
            elif asn in site.asns.all():
                self.log_info(f"Skipping ASN {asn} for site {site}; already assigned")
                continue

            # Assign the ASN to the Site
            self.log_success(f"Assigning ASN {asn} to site {site}")
            site.asns.add(asn)
            asns_assigned += 1

            # Clear legacy ASN field on Site (if enabled)
            if data['clear_site_field']:
                self.log_debug(f"Clearing legacy ASN field for site {site}")
                Site.objects.filter(pk=site.pk).update(asn=None)

        self.log_success(f"Created {asns_created} ASNs")
        self.log_success(f"Assigned {asns_assigned} ASNs to sites")
