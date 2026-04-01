from datetime import datetime, date
from pydantic import BaseModel


class SalesforceAccount(BaseModel):
    """
    Salesforce Account record.

    Base fields (always returned): Id, Name, Industry, Website

    Extra fields available via extra_fields parameter (use the SOQL name):
      Phone, Type, BillingStreet, BillingCity, BillingState,
      BillingPostalCode, BillingCountry, NumberOfEmployees,
      AnnualRevenue, Description, CreatedDate, LastModifiedDate

    Filterable fields (base + extra, use in filters parameter):
      Name, Industry, Website, Phone, Type, BillingStreet, BillingCity,
      BillingState, BillingPostalCode, BillingCountry,
      NumberOfEmployees (numeric =), AnnualRevenue (numeric =)
    """
    # Base fields — always returned
    id: str                                  # Id
    name: str                                # Name
    industry: str | None                     # Industry
    website: str | None                      # Website
    # Optional — populated when requested via extra_fields
    phone: str | None = None                 # Phone
    type: str | None = None                  # Type
    billing_street: str | None = None        # BillingStreet
    billing_city: str | None = None          # BillingCity
    billing_state: str | None = None         # BillingState
    billing_postal_code: str | None = None   # BillingPostalCode
    billing_country: str | None = None       # BillingCountry
    number_of_employees: int | None = None   # NumberOfEmployees
    annual_revenue: float | None = None      # AnnualRevenue
    description: str | None = None           # Description
    created_date: str | None = None          # CreatedDate
    last_modified_date: str | None = None    # LastModifiedDate


class SalesforceContact(BaseModel):
    """
    Salesforce Contact record.

    Base fields (always returned): Id, FirstName, LastName, Email, Account.Name

    Extra fields available via extra_fields parameter (use the SOQL name):
      Phone, MobilePhone, Title, Department, MailingStreet, MailingCity,
      MailingState, MailingPostalCode, MailingCountry, LeadSource, CreatedDate

    Filterable fields:
      FirstName, LastName, Email, Account.Name, Phone, Title, Department,
      MailingCity, MailingState, MailingPostalCode, MailingCountry,
      LeadSource, CreatedDate
    """
    # Base fields
    id: str                                  # Id
    first_name: str | None                   # FirstName
    last_name: str                           # LastName
    email: str | None                        # Email
    account_name: str | None                 # Account.Name
    # Optional
    phone: str | None = None                 # Phone
    mobile_phone: str | None = None          # MobilePhone
    title: str | None = None                 # Title
    department: str | None = None            # Department
    mailing_street: str | None = None        # MailingStreet
    mailing_city: str | None = None          # MailingCity
    mailing_state: str | None = None         # MailingState
    mailing_postal_code: str | None = None   # MailingPostalCode
    mailing_country: str | None = None       # MailingCountry
    lead_source: str | None = None           # LeadSource
    created_date: str | None = None          # CreatedDate


class SalesforceOpportunity(BaseModel):
    """
    Salesforce Opportunity record.

    Base fields (always returned): Id, Name, StageName, Amount, CloseDate, Account.Name

    Extra fields available via extra_fields parameter (use the SOQL name):
      Probability, Type, LeadSource, ForecastCategory, Description,
      CreatedDate, LastModifiedDate

    Filterable fields:
      Name, StageName, Account.Name, Type, LeadSource, ForecastCategory,
      Amount (numeric =), Probability (numeric =)
    """
    # Base fields
    id: str                                  # Id
    name: str                                # Name
    stage: str                               # StageName
    amount: float | None                     # Amount
    close_date: date | None                  # CloseDate
    account_name: str | None                 # Account.Name
    # Optional
    probability: float | None = None         # Probability
    type: str | None = None                  # Type
    lead_source: str | None = None           # LeadSource
    forecast_category: str | None = None     # ForecastCategory
    description: str | None = None           # Description
    created_date: str | None = None          # CreatedDate
    last_modified_date: str | None = None    # LastModifiedDate


class SalesforceCase(BaseModel):
    """
    Salesforce Case record.

    Base fields (always returned): Id, Subject, Status, Priority, Account.Name, CreatedDate

    Extra fields available via extra_fields parameter (use the SOQL name):
      Description, Origin, Type, Reason, ClosedDate, LastModifiedDate

    Filterable fields:
      Subject, Status, Priority, Account.Name, Description, Origin,
      Type, Reason
    """
    # Base fields
    id: str                                  # Id
    case_number: str | None                  # CaseNumber
    subject: str                             # Subject
    status: str                              # Status
    priority: str | None                     # Priority
    account_name: str | None                 # Account.Name
    created_date: datetime | None            # CreatedDate
    # Optional
    description: str | None = None           # Description
    origin: str | None = None                # Origin
    type: str | None = None                  # Type
    reason: str | None = None                # Reason
    closed_date: str | None = None           # ClosedDate
    last_modified_date: str | None = None    # LastModifiedDate


class SalesforceLead(BaseModel):
    """
    Salesforce Lead record.

    Base fields (always returned): Id, FirstName, LastName, Email, Company, Status

    Extra fields available via extra_fields parameter (use the SOQL name):
      Phone, MobilePhone, Title, Industry, LeadSource, Street, City,
      State, PostalCode, Country, Rating, NumberOfEmployees,
      AnnualRevenue, CreatedDate

    Filterable fields:
      FirstName, LastName, Email, Company, Status, Phone, Title,
      Industry, LeadSource, City, State, PostalCode, Country, Rating,
      NumberOfEmployees (numeric =), AnnualRevenue (numeric =)
    """
    # Base fields
    id: str                                  # Id
    first_name: str | None                   # FirstName
    last_name: str                           # LastName
    email: str | None                        # Email
    company: str | None                      # Company
    status: str | None                       # Status
    # Optional
    phone: str | None = None                 # Phone
    mobile_phone: str | None = None          # MobilePhone
    title: str | None = None                 # Title
    industry: str | None = None              # Industry
    lead_source: str | None = None           # LeadSource
    street: str | None = None                # Street
    city: str | None = None                  # City
    state: str | None = None                 # State
    postal_code: str | None = None           # PostalCode
    country: str | None = None               # Country
    rating: str | None = None                # Rating
    number_of_employees: int | None = None   # NumberOfEmployees
    annual_revenue: float | None = None      # AnnualRevenue
    created_date: str | None = None          # CreatedDate
