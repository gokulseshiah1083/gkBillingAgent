# Example Prompts and Response Templates

## Overview
This document provides example prompts and expected responses for the AI Billing Investigation Agent, demonstrating various investigation scenarios and response formats.

## Single Transaction Investigation

### Example 1: Fee Dispute
**Prompt:**
```
Why was transaction TXN202401154789 charged $12.50 instead of the expected $8.00?
```

**Expected Response:**
```
Investigation Results for TXN202401154789:

**Answer:**
The transaction was charged $12.50 instead of $8.00 due to a foreign transaction fee of $4.50 being applied. The base interchange fee of $8.00 was correctly calculated, but an additional foreign currency assessment was added because the transaction was processed in EUR.

**Root Cause:**
- Base interchange rate: $8.00 (correct)
- Foreign transaction fee: $4.50 (2% of $225.00 transaction amount)
- Total: $12.50

**Evidence:**
- Transaction currency: EUR (originated in France)
- Merchant category: 5812 (Restaurants)
- Card type: World Elite (has foreign transaction fee)
- Fee rule: FTF_EUROPEAN_2PCT applied correctly

**Billing Rules Applied:**
1. Interchange Rate: RESTAURANT_WORLD_ELITE_EUROPE
2. Foreign Transaction Fee: FTF_EUROPEAN_2PCT
3. Assessment Fee: STANDARD_ASSESSMENT

**Next Steps:**
1. Verify cardholder agreement for foreign transaction fees
2. Check if customer has foreign transaction fee waiver
3. Review merchant location classification
4. Consider fee reversal if customer was not informed

**Similar Cases:**
- Case #23456: Similar restaurant transaction in Italy (resolved with fee reversal)
- Case #23489: European e-commerce transaction (fee upheld)
- Case #23512: UK transaction processed as foreign (error corrected)

**Confidence:** 94%
```

### Example 2: Authorization vs Settlement
**Prompt:**
```
Transaction 1234567890123456 was authorized for $45.00 but settled for $47.25. Why the difference?
```

**Expected Response:**
```
Investigation Results for PAN 123456******3456:

**Answer:**
The $2.25 difference between authorization ($45.00) and settlement ($47.25) is due to a dynamic currency conversion (DCC) fee applied at settlement time. The customer chose to pay in their home currency (USD) rather than the merchant's currency (GBP).

**Root Cause:**
- Authorization amount: $45.00 (estimated USD conversion)
- Settlement amount: £37.50 GBP = $47.25 USD (actual conversion + DCC fee)
- DCC fee: $1.50 (3% of transaction amount)
- Currency conversion difference: $0.75

**Evidence:**
- Merchant location: United Kingdom
- Original currency: GBP
- Settlement timestamp: 2024-01-15 14:32:10 UTC
- DCC indicator: YES (customer opted in)
- Conversion rate used: 1.26 USD/GBP

**Billing Rules Applied:**
1. DCC Service Fee: DCC_3PCT
2. Currency Conversion: VISA_CONVERSION_RATE
3. Cross-Border Assessment: CROSS_BORDER_EU_TO_US

**Next Steps:**
1. Verify DCC disclosure was provided to customer
2. Check customer's DCC preference settings
3. Review merchant DCC compliance
4. Document currency conversion rate used

**Similar Cases:**
- Case #23678: UK transaction with DCC (fee upheld)
- Case #23690: European transaction without proper DCC disclosure (reversal processed)

**Confidence:** 91%
```

## PAN Range Investigation

### Example 3: Issuer PAN Range Issue
**Prompt:**
```
Show all billing anomalies for PAN range 542418 to 542425 in the last 48 hours
```

**Expected Response:**
```
PAN Range Analysis: 542418XXXXXX to 542425XXXXXX (Last 48 Hours)

**Summary:**
Found 3,247 transactions with 47 anomalies (1.45% anomaly rate). Two main issues identified:

1. **Incorrect Assessment Fees** (32 cases)
   - Assessment fee of 0.13% applied instead of 0.12%
   - Impact: Average overcharge of $0.23 per transaction
   - Total impact: $7.36

2. **Late Fee Application Errors** (15 cases)
   - Late fees applied to current accounts
   - Impact: Average incorrect fee of $35.00
   - Total impact: $525.00

**Detailed Findings:**

**Issue 1: Assessment Fee Calculation Error**
- **Affected PANs:** 542418, 542419, 542420, 542421
- **Root Cause:** Recent system update changed assessment rate table
- **Time Period:** 2024-01-14 09:15:00 to 2024-01-15 09:15:00
- **Rule Applied:** ASSESSMENT_013PCT (should be ASSESSMENT_012PCT)

**Evidence:**
- Feeder file: BILL_FEED_20240115_02
- Error timestamp: 2024-01-14 09:15:32 UTC
- Configuration change: ASSESSMENT_RATE_UPDATE_20240114

**Issue 2: Late Fee Application Error**
- **Affected PANs:** 542422, 542423, 542424, 542425
- **Root Cause:** Account status lookup failure during batch processing
- **Time Period:** 2024-01-15 02:00:00 to 2024-01-15 06:00:00
- **Rule Applied:** LATE_FEE_35 (incorrectly applied)

**Evidence:**
- Batch job: LATE_FEE_BATCH_20240115
- Error log: ACCOUNT_STATUS_LOOKUP_TIMEOUT
- Recovery: Manual status correction completed

**Recommended Actions:**
1. **Immediate:** Generate reversal file for assessment fee overcharges ($7.36 total)
2. **Immediate:** Process reversals for incorrect late fees ($525.00 total)
3. **Short-term:** Fix assessment rate table configuration
4. **Long-term:** Implement account status lookup timeout handling
5. **Prevention:** Add validation for assessment rate changes

**System Impact:**
- Total financial impact: $532.36
- Customer impact: 47 affected cardholders
- Processing impact: Requires batch reversal processing

**Similar Incidents:**
- Incident #INC-2024-0142: Assessment rate error (January 2024)
- Incident #INC-2023-0891: Late fee batch error (August 2023)

**Confidence:** 96%
```

## Issuer Level Investigation

### Example 4: Issuer Billing Pattern Analysis
**Prompt:**
```
Analyze billing patterns for Chase Bank transactions over $1000 in the past month
```

**Expected Response:**
```
Issuer Analysis: Chase Bank (High-Value Transactions, Past Month)

**Overview:**
Analyzed 124,567 Chase Bank transactions over $1000 from 2023-12-15 to 2024-01-15. Identified several billing patterns and anomalies.

**Key Metrics:**
- Total transaction volume: $187.3M
- Average transaction amount: $1,503
- Total billing revenue: $2.84M (1.52% effective rate)
- Anomaly rate: 0.87% (1,084 transactions)

**Pattern Analysis:**

**1. Transaction Distribution by Amount:**
- $1,000-$2,500: 89,234 transactions (71.6%)
- $2,500-$5,000: 28,456 transactions (22.8%)
- $5,000-$10,000: 5,876 transactions (4.7%)
- $10,000+: 1,001 transactions (0.8%)

**2. Billing Rate Variations by Category:**
- Travel/Airlines: 1.78% (higher due to premium cards)
- Retail: 1.45% (standard rate)
- Restaurants: 1.62% (enhanced rate for premium cards)
- Services: 1.38% (lower rate for B2B transactions)

**3. Identified Anomalies:**

**Anomaly A: Premium Card Misclassification**
- **Count:** 456 transactions
- **Issue:** Sapphire Reserve cards billed at standard rates instead of premium rates
- **Impact:** $23,450 underbilling (0.52% per transaction)
- **Pattern:** Occurs mainly in travel category

**Evidence:**
- Card BIN range: 426684XXXXXX
- Expected rate: 2.10% (premium travel)
- Applied rate: 1.45% (standard)
- Time period: 2023-12-20 to 2024-01-10

**Anomaly B: Cross-Border Fee Inconsistency**
- **Count:** 128 transactions
- **Issue:** Cross-border fees not applied to international transactions
- **Impact:** $8,920 underbilling
- **Pattern:** Mainly European transactions

**Evidence:**
- Merchant countries: FR, DE, IT, ES
- Missing fee: CROSS_BORDER_EU_1PCT
- BIN ranges: 414720XXXXXX, 414721XXXXXX

**4. Seasonal Trends:**
- Holiday period (Dec 20-31): 23% increase in high-value transactions
- Post-holiday (Jan 1-15): 18% decrease, but higher average amounts
- Weekend transactions: 12% higher billing rates (more premium card usage)

**Recommendations:**
1. **Immediate:** Correct premium card misclassification (recover $23,450)
2. **Immediate:** Fix cross-border fee application logic (recover $8,920)
3. **Short-term:** Implement card product validation in billing pipeline
4. **Long-term:** Enhanced monitoring for premium card rate compliance

**Financial Impact:**
- Total underbilling identified: $32,370
- Potential monthly recovery: $32,370
- Annual impact if unresolved: ~$388,440

**Similar Analyses:**
- Chase Bank Q3 2023: Similar premium card issues found and corrected
- Bank of America Q4 2023: Cross-border fee issues resolved
- Citibank Q1 2024: No similar anomalies detected

**Confidence:** 93%
```

## Rule and Policy Questions

### Example 5: Policy Clarification
**Prompt:**
```
What are the interchange rates for restaurant transactions in the US for World Elite cards?
```

**Expected Response:**
```
Interchange Rate Information: US Restaurants - World Elite Cards

**Current Interchange Rates (Effective 2024-01-01):**

**Standard Restaurant Rates:**
- **Base Rate:** 1.80% + $0.10 per transaction
- **Small Ticket (<$10):** 2.10% + $0.05
- **Large Ticket (>$500):** 1.65% + $0.15

**Enhanced Rates for World Elite:**
- **Base Enhancement:** +0.15% to base rate
- **Premium Restaurant Enhancement:** +0.25% for fine dining (MCC 5812)
- **International Enhancement:** +0.20% for non-US merchants

**Rate Calculation Examples:**
- $25.00 restaurant purchase: 1.95% + $0.10 = $0.59
- $150.00 fine dining: 2.05% + $0.10 = $3.18
- $8.00 coffee shop: 2.25% + $0.05 = $0.23

**Applicable Rules and Policies:**
1. **Mastercard Rule 5.11.1:** Restaurant interchange rate structure
2. **World Elite Premium Benefits:** Enhanced rates for premium card products
3. **US Region Pricing:** Regional rate adjustments for US market
4. **MCC-Specific Rates:** Merchant category classification impacts

**Conditions and Exceptions:**
- **Small Ticket Exception:** Applies to transactions <$10.00
- **Volume Discounts:** Available for high-volume merchants (>10,000 transactions/month)
- **Regulated Debit Exemption:** Different rates apply for regulated debit cards
- **Government Programs:** Special rates for government assistance programs

**Recent Changes:**
- **2024-01-01:** Base rate increased from 1.75% to 1.80%
- **2023-10-01:** World Elite enhancement increased from +0.10% to +0.15%
- **2023-07-01:** Small ticket threshold changed from $15 to $10

**Compliance Notes:**
- Rates are reviewed quarterly by Mastercard pricing committee
- Merchants must be properly classified under MCC 5812 (restaurants) or 5813 (drinking places)
- World Elite card validation required for enhanced rates
- Geographic validation required for US regional rates

**Related Documentation:**
- Mastercard Interchange Rate Guide 2024
- World Elite Product Manual Section 3.2
- US Regional Pricing Schedule Q1 2024
- MCC Classification Guidelines

**Next Steps:**
1. Verify merchant MCC classification
2. Confirm card product tier (World Elite vs Platinum)
3. Check transaction location for regional rate application
4. Review volume discount eligibility if applicable

**Confidence:** 98%
```

## Error and Exception Handling

### Example 6: System Error Investigation
**Prompt:**
```
Investigate billing errors for feeder file BILL_FEED_20240115_03
```

**Expected Response:**
```
Feeder File Investigation: BILL_FEED_20240115_03

**File Overview:**
- **File Name:** BILL_FEED_20240115_03
- **Processing Time:** 2024-01-15 03:15:42 UTC
- **Record Count:** 45,678 transactions
- **Error Count:** 1,234 errors (2.7% error rate)
- **Status:** Partially processed with manual intervention required

**Error Analysis:**

**Category 1: Missing PAN Data (847 errors - 68.6%)**
- **Description:** PAN field null or invalid format
- **Impact:** Transactions could not be processed
- **Root Cause:** Data extraction issue from source system
- **Recovery:** Manual PAN lookup required

**Sample Errors:**
```
Record 12567: PAN=NULL, Amount=$125.50, Merchant=AMAZON
Record 12890: PAN=INVALID_FORMAT, Amount=$89.99, Merchant=WALMART
```

**Category 2: Amount Validation Errors (234 errors - 19.0%)**
- **Description:** Transaction amounts outside valid ranges
- **Impact:** Transactions flagged for manual review
- **Root Cause:** Currency conversion errors
- **Recovery:** Automatic correction possible for 80% of cases

**Sample Errors:**
```
Record 13456: Amount=$-25.00 (negative amount)
Record 13578: Amount=$999999.99 (excessive amount)
```

**Category 3: Merchant Category Issues (153 errors - 12.4%)**
- **Description:** Invalid or missing MCC codes
- **Impact:** Incorrect interchange rate application
- **Root Cause:** Merchant database synchronization issue
- **Recovery:** MCC lookup and correction required

**System Impact:**
- **Financial Impact:** $45,678.90 in unprocessed transactions
- **Customer Impact:** 1,234 customers affected
- **Processing Delay:** 4.5 hours additional processing time
- **Manual Intervention:** 12 analyst hours required

**Root Cause Analysis:**
1. **Primary Cause:** Database connection timeout during data extraction
2. **Contributing Factor:** Insufficient retry logic for failed connections
3. **System Issue:** Memory leak in feeder file processor
4. **Process Gap:** No pre-validation of source data quality

**Immediate Actions Taken:**
1. **03:45 UTC:** Paused processing of feeder file
2. **04:15 UTC:** Identified database connectivity issues
3. **05:30 UTC:** Implemented temporary connection pool increase
4. **06:00 UTC:** Resumed processing with enhanced error handling

**Recommended Next Steps:**
1. **Immediate:** Complete processing of remaining records with manual intervention
2. **Today:** Fix database connection pooling configuration
3. **This Week:** Implement pre-validation checks for feeder files
4. **Next Sprint:** Add comprehensive error recovery mechanisms

**Prevention Measures:**
1. **Enhanced Monitoring:** Real-time feeder file quality checks
2. **Improved Retry Logic:** Exponential backoff for database connections
3. **Data Validation:** Pre-processing validation of all required fields
4. **Alerting:** Automated alerts for high error rates (>1%)

**Similar Incidents:**
- Incident #INC-2024-0089: Similar feeder file issues (January 8, 2024)
- Incident #INC-2023-0945: Database connection timeout (December 2023)

**Financial Recovery:**
- **Expected Recovery:** 95% of unprocessed amount ($43,395.00)
- **Time to Recovery:** 2 business days
- **Cost of Recovery:** $2,500 in analyst resources

**Confidence:** 89%
```

## Response Format Guidelines

### Standard Response Structure
All responses should follow this structure:

1. **Clear Answer**: Direct response to the user's question
2. **Root Cause Analysis**: Explanation of why the issue occurred
3. **Evidence**: Supporting data and documentation
4. **Rules Applied**: Relevant billing rules and policies
5. **Next Steps**: Recommended actions and follow-ups
6. **Similar Cases**: Relevant historical cases
7. **Confidence Score**: Confidence level in the analysis

### Confidence Score Guidelines
- **95-100%**: High confidence with strong evidence
- **85-94%**: Good confidence with adequate evidence
- **70-84%**: Moderate confidence with some uncertainty
- **Below 70%**: Low confidence, requires additional investigation

### Compliance Notes
- All PANs are masked in responses (show first 6, last 4 digits)
- Sensitive customer information is never disclosed
- Financial amounts are rounded to 2 decimal places
- All responses are logged for audit purposes
