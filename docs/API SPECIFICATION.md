
1. API Overview
1.1 API Design Principles
RESTful: Following REST architectural style

Versioned: Semantic versioning (v1, v2, etc.)

Secure: HTTPS only, JWT authentication

Documented: OpenAPI 3.0 specification

Consistent: Standardized error responses

Performant: Response compression, caching

1.2 Base Information
Base URL: https://api.wildautomations.com/v1

Protocol: HTTPS (TLS 1.3)

Content-Type: application/json

Authentication: Bearer JWT Token

Rate Limiting: 1000 requests/minute per user

2. Authentication API
2.1 Register User
text
POST /auth/register
Description: Register a new user account

Request Body:

json
{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "phone": "+1234567890",
    "full_name": "John Doe"
}
Response:

json
{
    "user_id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "created_at": "2024-01-15T10:00:00Z",
    "message": "User registered successfully"
}
Error Responses:

400: Invalid input

409: User already exists

500: Internal server error

2.2 Login
text
POST /auth/login
Description: Authenticate user and get access token

Request Body:

json
{
    "email": "user@example.com",
    "password": "SecurePassword123!"
}
Response:

json
{
    "access_token": "jwt_token_here",
    "refresh_token": "refresh_token_here",
    "expires_in": 3600,
    "token_type": "Bearer"
}
Error Responses:

401: Invalid credentials

403: Account locked

500: Internal server error

2.3 Refresh Token
text
POST /auth/refresh
Description: Refresh expired access token

Request Body:

json
{
    "refresh_token": "refresh_token_here"
}
Response:

json
{
    "access_token": "new_jwt_token_here",
    "expires_in": 3600
}
2.4 Logout
text
POST /auth/logout
Description: Invalidate current session

Request Headers:

text
Authorization: Bearer jwt_token_here
Response:

json
{
    "message": "Logged out successfully"
}
3. User Profile API
3.1 Get Profile
text
GET /profile
Description: Get current user's profile

Request Headers:

text
Authorization: Bearer jwt_token_here
Response:

json
{
    "user_id": "uuid",
    "email": "user@example.com",
    "phone": "+1234567890",
    "full_name": "John Doe",
    "avatar_url": "https://...",
    "country": "United States",
    "city": "New York",
    "education": {
        "level": "Bachelor's",
        "field": "Computer Science",
        "institution": "MIT"
    },
    "skills": ["Python", "Machine Learning", "Data Science"],
    "languages": ["English", "Spanish"],
    "preferences": {
        "domains": ["jobs", "education", "immigration"],
        "countries": ["USA", "Canada"],
        "visa_sponsorship": true
    },
    "created_at": "2024-01-15T10:00:00Z"
}
3.2 Update Profile
text
PUT /profile
Description: Update current user's profile

Request Headers:

text
Authorization: Bearer jwt_token_here
Request Body:

json
{
    "full_name": "John Smith",
    "country": "USA",
    "city": "San Francisco",
    "education": {
        "level": "Master's",
        "field": "Data Science",
        "institution": "Stanford"
    },
    "skills": ["Python", "SQL", "Machine Learning"],
    "languages": ["English"],
    "preferences": {
        "domains": ["jobs", "real_estate"],
        "countries": ["USA", "UK", "Germany"],
        "visa_sponsorship": true
    }
}
Response:

json
{
    "message": "Profile updated successfully",
    "profile": {
        "user_id": "uuid",
        "email": "user@example.com",
        "full_name": "John Smith",
        "country": "USA",
        "city": "San Francisco"
    }
}
3.3 Get Preferences
text
GET /profile/preferences
Description: Get user's notification and search preferences

Response:

json
{
    "notifications": {
        "enabled": true,
        "channels": ["email", "whatsapp"],
        "real_time_alerts": true,
        "daily_summary": true,
        "weekly_summary": false
    },
    "saved_searches": [
        {
            "id": "uuid",
            "name": "Data Science Jobs in Germany",
            "query": "Data Science visa sponsorship Germany",
            "filters": {
                "country": "Germany",
                "visa_sponsorship": true
            },
            "schedule": "daily",
            "created_at": "2024-01-15T10:00:00Z"
        }
    ],
    "domains": ["jobs", "real_estate", "vehicles"],
    "custom_filters": {
        "salary_range": {
            "min": 80000,
            "max": 120000,
            "currency": "USD"
        },
        "locations": ["USA", "Canada"]
    }
}
4. Search API
4.1 Search Opportunities
text
POST /search
Description: Search for opportunities

Request Headers:

text
Authorization: Bearer jwt_token_here
Request Body:

json
{
    "query": "Data Science visa sponsorship jobs in Germany",
    "filters": {
        "domains": ["jobs"],
        "countries": ["Germany"],
        "visa_sponsorship": true,
        "experience_level": ["mid", "senior"],
        "salary_range": {
            "min": 80000,
            "max": 120000,
            "currency": "EUR"
        },
        "remote": true,
        "posted_within_days": 7
    },
    "pagination": {
        "page": 1,
        "limit": 20
    },
    "sort": {
        "field": "match_score",
        "order": "desc"
    }
}
Response:

json
{
    "results": [
        {
            "id": "uuid",
            "title": "Senior Data Scientist",
            "domain": "jobs",
            "source": "LinkedIn",
            "company": {
                "name": "TechCorp GmbH",
                "website": "https://techcorp.com"
            },
            "location": {
                "country": "Germany",
                "city": "Berlin"
            },
            "salary": {
                "min": 90000,
                "max": 120000,
                "currency": "EUR"
            },
            "visa_sponsorship": true,
            "match_score": 0.92,
            "posted_date": "2024-01-14T08:00:00Z",
            "expiry_date": "2024-02-14T08:00:00Z",
            "url": "https://linkedin.com/jobs/123"
        }
    ],
    "pagination": {
        "total": 156,
        "page": 1,
        "limit": 20,
        "pages": 8
    },
    "metadata": {
        "query_time_ms": 150,
        "cache_hit": false,
        "intent_detected": {
            "intent": "search",
            "domains": ["jobs"],
            "confidence": 0.95
        }
    }
}
4.2 Advanced Search
text
POST /search/advanced
Description: Advanced search with complex filters

Request Body:

json
{
    "query": "Find me a Toyota Corolla below AED 40,000 in Dubai",
    "filters": {
        "domains": ["vehicles"],
        "vehicle_specific": {
            "make": "Toyota",
            "model": "Corolla",
            "max_price": 40000,
            "currency": "AED",
            "location": "Dubai",
            "condition": ["used", "certified"],
            "max_mileage": 100000,
            "transmission": ["automatic", "manual"],
            "year_range": {
                "min": 2018,
                "max": 2023
            }
        }
    },
    "pagination": {
        "page": 1,
        "limit": 10
    }
}
4.3 Get Search Suggestions
text
GET /search/suggestions?q=Data Science
Description: Get autocomplete suggestions

Query Parameters:

q: Search query (min 2 characters)

limit: Max suggestions (default: 10)

Response:

json
{
    "suggestions": [
        "Data Science jobs in Germany",
        "Data Science visa sponsorship",
        "Data Science internships",
        "Data Science remote jobs",
        "Data Science salary range"
    ],
    "domains": {
        "jobs": 45,
        "education": 12,
        "scholarships": 8
    }
}
5. Opportunities API
5.1 Get Opportunity Details
text
GET /opportunities/{opportunity_id}
Description: Get detailed information about an opportunity

Path Parameters:

opportunity_id: UUID of the opportunity

Response:

json
{
    "id": "uuid",
    "title": "Senior Data Scientist",
    "domain": "jobs",
    "source": "LinkedIn",
    "source_id": "12345",
    "description": "We are looking for a Senior Data Scientist...",
    "company": {
        "name": "TechCorp GmbH",
        "website": "https://techcorp.com",
        "industry": "Technology",
        "size": "100-500"
    },
    "location": {
        "country": "Germany",
        "city": "Berlin",
        "address": "Berlin, Germany",
        "remote": true
    },
    "salary": {
        "min": 90000,
        "max": 120000,
        "currency": "EUR",
        "period": "yearly"
    },
    "requirements": {
        "education": "Master's degree in Computer Science or related",
        "experience": "5+ years",
        "skills": ["Python", "SQL", "Machine Learning", "Deep Learning"],
        "languages": ["English", "German"]
    },
    "visa_sponsorship": true,
    "posted_date": "2024-01-14T08:00:00Z",
    "expiry_date": "2024-02-14T08:00:00Z",
    "application_url": "https://techcorp.com/careers/123",
    "status": "active",
    "match_score": 0.92,
    "similar_opportunities": [
        {
            "id": "uuid2",
            "title": "Data Scientist",
            "company": "DataCorp",
            "match_score": 0.85
        }
    ]
}
5.2 Save Opportunity
text
POST /opportunities/save
Description: Save an opportunity to user's saved list

Request Body:

json
{
    "opportunity_id": "uuid"
}
Response:

json
{
    "message": "Opportunity saved successfully",
    "saved_at": "2024-01-15T10:00:00Z"
}
5.3 Remove Saved Opportunity
text
DELETE /opportunities/save/{opportunity_id}
Description: Remove an opportunity from saved list

Response:

json
{
    "message": "Opportunity removed from saved list"
}
5.4 Get Saved Opportunities
text
GET /opportunities/saved
Description: Get user's saved opportunities

Query Parameters:

page: Page number (default: 1)

limit: Items per page (default: 20)

domain: Filter by domain

Response:

json
{
    "saved_opportunities": [
        {
            "id": "uuid",
            "title": "Senior Data Scientist",
            "company": "TechCorp GmbH",
            "domain": "jobs",
            "saved_at": "2024-01-15T10:00:00Z",
            "match_score": 0.92
        }
    ],
    "pagination": {
        "total": 5,
        "page": 1,
        "limit": 20
    }
}
6. Notifications API
6.1 Get Notifications
text
GET /notifications
Description: Get user's notifications

Query Parameters:

status: Filter by status (pending, sent, read, failed)

limit: Items per page (default: 20)

offset: Offset for pagination

Response:

json
{
    "notifications": [
        {
            "id": "uuid",
            "type": "opportunity_alert",
            "title": "New Job Match: Data Scientist",
            "message": "A new Data Scientist position has been posted...",
            "opportunity_id": "uuid",
            "channel": "whatsapp",
            "status": "read",
            "sent_at": "2024-01-15T09:00:00Z",
            "read_at": "2024-01-15T09:05:00Z"
        }
    ],
    "pagination": {
        "total": 25,
        "limit": 20,
        "offset": 0
    }
}
6.2 Update Notification Preferences
text
PUT /notifications/preferences
Description: Update notification preferences

Request Body:

json
{
    "notifications_enabled": true,
    "channels": ["whatsapp"],
    "real_time_alerts": true,
    "daily_summary": true,
    "weekly_summary": false,
    "domains": ["jobs", "real_estate", "vehicles"],
    "frequency": {
        "jobs": "daily",
        "real_estate": "weekly",
        "vehicles": "daily"
    }
}
Response:

json
{
    "message": "Notification preferences updated successfully"
}
7. WhatsApp API
7.1 Send WhatsApp Message
text
POST /whatsapp/send
Description: Send a WhatsApp message

Request Headers:

text
Authorization: Bearer jwt_token_here
Request Body:

json
{
    "to": "+1234567890",
    "message": "Hello! Here's a new opportunity...",
    "type": "text",
    "buttons": [
        {
            "label": "View Details",
            "url": "https://wildautomations.com/opportunity/123"
        },
        {
            "label": "Save",
            "action": "save_opportunity"
        }
    ]
}
Response:

json
{
    "message_id": "uuid",
    "status": "sent",
    "sent_at": "2024-01-15T10:00:00Z"
}
7.2 Process WhatsApp Webhook
text
POST /whatsapp/webhook
Description: Endpoint for WhatsApp webhook callbacks

Request Body (from WhatsApp):

json
{
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "123456789",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "1234567890",
                            "phone_number_id": "0987654321"
                        },
                        "contacts": [
                            {
                                "profile": {
                                    "name": "John Doe"
                                },
                                "wa_id": "1234567890"
                            }
                        ],
                        "messages": [
                            {
                                "from": "1234567890",
                                "id": "wamid.123456",
                                "timestamp": "1705310400",
                                "text": {
                                    "body": "Find me data science jobs in Germany"
                                },
                                "type": "text"
                            }
                        ]
                    }
                }
            ]
        }
    ]
}
Response:

json
{
    "status": "received",
    "message_id": "wamid.123456",
    "response": {
        "intent": "search",
        "results": 15,
        "top_result": "Senior Data Scientist at TechCorp"
    }
}
8. Admin API
8.1 Get System Health
text
GET /admin/health
Description: Get system health status

Request Headers:

text
Authorization: Bearer jwt_token_here
Response:

json
{
    "status": "healthy",
    "components": {
        "database": {
            "status": "healthy",
            "connections": 25,
            "max_connections": 100,
            "latency_ms": 5
        },
        "redis": {
            "status": "healthy",
            "connections": 10,
            "memory_usage": 45.2,
            "hit_rate": 0.92
        },
        "celery": {
            "status": "healthy",
            "active_workers": 5,
            "queue_size": 123,
            "failed_tasks": 0
        },
        "ai_services": {
            "status": "healthy",
            "available_models": 7,
            "avg_latency_ms": 800
        },
        "scrapers": {
            "status": "healthy",
            "active_sources": 25,
            "last_success": "2024-01-15T09:00:00Z"
        }
    },
    "timestamp": "2024-01-15T10:00:00Z"
}
8.2 Get Source Status
text
GET /admin/sources
Description: Get all source statuses

Response:

json
{
    "sources": [
        {
            "id": "linkedin_jobs",
            "name": "LinkedIn Jobs",
            "domain": "jobs",
            "type": "apify",
            "status": "running",
            "last_scrape": "2024-01-15T09:30:00Z",
            "next_scrape": "2024-01-15T10:00:00Z",
            "items_collected": 1254,
            "success_rate": 0.98,
            "error_count": 0
        },
        {
            "id": "dubizzle_cars",
            "name": "Dubizzle Cars",
            "domain": "vehicles",
            "type": "http",
            "status": "failed",
            "last_scrape": "2024-01-15T08:30:00Z",
            "next_scrape": "2024-01-15T09:00:00Z",
            "items_collected": 0,
            "success_rate": 0.0,
            "error_count": 2
        }
    ],
    "total_sources": 25,
    "active_sources": 23,
    "failed_sources": 1,
    "paused_sources": 1
}
8.3 Trigger Manual Scrape
text
POST /admin/sources/{source_id}/scrape
Description: Trigger manual scraping for a source

Path Parameters:

source_id: ID of the source

Response:

json
{
    "status": "started",
    "job_id": "uuid",
    "source_id": "linkedin_jobs",
    "started_at": "2024-01-15T10:00:00Z",
    "estimated_duration": "5 minutes"
}
8.4 Get System Metrics
text
GET /admin/metrics
Description: Get system performance metrics

Query Parameters:

period: Time period (hour, day, week)

metric_type: Type of metrics (general, performance, cost)

Response:

json
{
    "general": {
        "users": {
            "total": 1523,
            "active": 234,
            "new_today": 12
        },
        "opportunities": {
            "total": 45678,
            "new_today": 234,
            "domains": {
                "jobs": 12345,
                "real_estate": 8765,
                "vehicles": 6543,
                "education": 4567,
                "immigration": 3456
            }
        }
    },
    "performance": {
        "api": {
            "avg_response_time_ms": 150,
            "p95_response_time_ms": 350,
            "error_rate": 0.02,
            "requests_per_second": 12.5
        },
        "ai": {
            "avg_latency_ms": 800,
            "model_usage": {
                "gemini-pro": 0.35,
                "claude-3-sonnet": 0.15,
                "gpt-4o": 0.10,
                "groq-mixtral": 0.40
            }
        },
        "scrapers": {
            "total_items": 1254,
            "success_rate": 0.94,
            "avg_duration_seconds": 120
        }
    },
    "cost": {
        "today": 25.50,
        "week": 156.75,
        "month": 625.30,
        "breakdown": {
            "ai": 15.30,
            "scraping": 8.50,
            "infrastructure": 1.70
        }
    }
}
9. Error Codes
9.1 Standard Error Response
json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable error message",
        "details": "Additional error details",
        "request_id": "uuid",
        "timestamp": "2024-01-15T10:00:00Z"
    }
}
9.2 Error Codes List
Code	HTTP Status	Description
AUTH_001	401	Invalid credentials
AUTH_002	403	Account locked
AUTH_003	401	Token expired
AUTH_004	401	Invalid token
VAL_001	400	Validation error
VAL_002	422	Invalid request data
NOTF_001	404	Resource not found
CONF_001	409	Resource conflict
RATE_001	429	Rate limit exceeded
PERM_001	403	Insufficient permissions
PERM_002	401	Authentication required
SYS_001	503	Service unavailable
SYS_002	500	Internal server error
AI_001	503	AI service unavailable
AI_002	504	AI request timeout
DB_001	503	Database unavailable
DB_002	504	Database timeout
10. Rate Limiting
10.1 Rate Limit Headers
text
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1705314000
Retry-After: 60
10.2 Rate Limit Rules
Endpoint	Limit	Period
/auth/*	10	1 minute
/profile/*	100	1 minute
/search	100	1 minute
/opportunities/*	200	1 minute
/notifications/*	100	1 minute
/admin/*	50	1 minute
