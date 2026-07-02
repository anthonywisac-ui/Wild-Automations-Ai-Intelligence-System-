CODING STANDARDS
1. Python Standards
1.1 Code Style
Python Coding Standards:
  
  Formatting:
    - Indentation: 4 spaces
    - Line length: 100 characters
    - Closing brackets: new line
    - Imports: group by standard library, third-party, local
    
  Naming Conventions:
    - Classes: CamelCase
    - Functions/Methods: snake_case
    - Variables: snake_case
    - Constants: UPPER_CASE
    - Private methods: _leading_underscore
  
  Documentation:
    - Docstrings: Google style
    - Type hints: Required
    - Comments: Explain why, not what
    - README: Comprehensive
  
  Code Quality:
    - Linting: flake8, pylint
    - Formatting: black
    - Type checking: mypy
    - Complexity: max cyclomatic 10
  
  Testing:
    - Unit tests: 90% coverage
    - Test files: test_*.py
    - Fixtures: pytest
    - Assertions: pytest assertions

1.2 Code Examples

# Good Example
"""
This module provides search functionality for opportunities.
"""

from typing import List, Optional, Dict
import logging
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Opportunity
from services.embedding_service import EmbeddingService


logger = logging.getLogger(__name__)


class SearchService:
    """
    Service for searching opportunities.
    
    Attributes:
        db_session: Database session for queries
        embedding_service: Service for generating embeddings
    """
    
    def __init__(self, db_session: Session, embedding_service: EmbeddingService):
        """Initialize search service."""
        self.db_session = db_session
        self.embedding_service = embedding_service
    
    async def search(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 20
    ) -> List[Opportunity]:
        """
        Search for opportunities.
        
        Args:
            query: Search query string
            filters: Optional search filters
            limit: Maximum number of results
            
        Returns:
            List of matching opportunities
            
        Raises:
            ValueError: If query is empty
            HTTPException: If search fails
        """
        if not query:
            raise ValueError("Query cannot be empty")
        
        try:
            # Generate embedding for query
            embedding = await self.embedding_service.generate_embedding(query)
            
            # Perform search
            results = self._perform_search(embedding, filters, limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise HTTPException(status_code=500, detail="Search failed")
    
    def _perform_search(
        self,
        embedding: List[float],
        filters: Optional[Dict],
        limit: int
    ) -> List[Opportunity]:
        """Internal search implementation."""
        # Implementation details
        pass
1.3 Type Hints
# Type hints examples
from typing import List, Dict, Optional, Union, Callable, Any
from typing_extensions import TypedDict

# Simple types
def process_data(data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    pass

# Complex types
class UserPreferences(TypedDict):
    notifications_enabled: bool
    domains: List[str]
    languages: List[str]
    budget_range: Dict[str, float]

def get_preferences(user_id: str) -> UserPreferences:
    pass

# Union types
def process_value(value: Union[int, float, str]) -> str:
    pass

# Optional types
def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    pass

# Callback types
def execute_with_retry(
    func: Callable[..., Any],
    max_retries: int = 3
) -> Any:
    pass

2. JavaScript/TypeScript Standards
2.1 Code Style
JavaScript/TypeScript Standards:
  
  Formatting:
    - Indentation: 2 spaces
    - Semicolons: required
    - Quotes: single quotes
    - Line length: 100 characters
    
  Naming Conventions:
    - Components: PascalCase
    - Functions: camelCase
    - Variables: camelCase
    - Constants: UPPER_CASE
    - Interfaces: PascalCase (I prefix)
    - Types: PascalCase
    
  React/Next.js:
    - Functional components: arrow functions
    - Hooks: use prefix
    - Props: destructuring
    - State: useState, useReducer
    - Effects: useEffect
    
  TypeScript:
    - Strict mode: enabled
    - Interfaces over types
    - Explicit return types
    - Avoid any type
    - Use const assertions
	
2.2 Code Examples
// Good Example
/**
 * Search component for finding opportunities.
 */

import React, { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Search as SearchIcon } from '@mui/icons-material';
import { useSearch } from '@/hooks/useSearch';
import { FilterPanel } from './FilterPanel';
import { SearchResults } from './SearchResults';
import type { SearchFilters } from '@/types/search';

interface SearchBarProps {
  initialQuery?: string;
  onSearch?: (query: string) => void;
  className?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  initialQuery = '',
  onSearch,
  className
}) => {
  const [query, setQuery] = useState<string>(initialQuery);
  const [showFilters, setShowFilters] = useState<boolean>(false);
  const { search, results, isLoading, filters, setFilters } = useSearch();
  const router = useRouter();

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    
    try {
      const searchResults = await search({ query, filters });
      if (onSearch) {
        onSearch(query);
      }
      router.push(`/search?q=${encodeURIComponent(query)}`);
    } catch (error) {
      console.error('Search failed:', error);
    }
  }, [query, filters, search, onSearch, router]);

  const handleKeyPress = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      handleSearch();
    }
  }, [handleSearch]);

  const handleFilterChange = useCallback((newFilters: SearchFilters) => {
    setFilters(newFilters);
    handleSearch();
  }, [setFilters, handleSearch]);

  return (
    <div className={`search-container ${className || ''}`}>
      <div className="search-input-wrapper">
        <SearchIcon className="search-icon" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Search opportunities..."
          className="search-input"
        />
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="filter-toggle"
        >
          Filters
        </button>
      </div>
      
      {showFilters && (
        <FilterPanel
          filters={filters}
          onChange={handleFilterChange}
          onClear={() => setFilters({})}
        />
      )}
      
      {isLoading && <div className="loading-spinner">Loading...</div>}
      
      {results && <SearchResults results={results} />}
    </div>
  );
};

SearchBar.displayName = 'SearchBar';
2.3 React Hooks
// Custom hook example
import { useState, useEffect, useCallback } from 'react';
import { api } from '@/utils/api';
import type { Opportunity } from '@/types/opportunity';

export const useSavedOpportunities = () => {
  const [saved, setSaved] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchSaved = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/opportunities/saved');
      setSaved(response.data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setLoading(false);
    }
  }, []);

  const saveOpportunity = useCallback(async (id: string) => {
    try {
      await api.post('/opportunities/save', { opportunity_id: id });
      await fetchSaved(); // Refresh list
      return true;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to save'));
      return false;
    }
  }, [fetchSaved]);

  const removeSaved = useCallback(async (id: string) => {
    try {
      await api.delete(`/opportunities/save/${id}`);
      await fetchSaved(); // Refresh list
      return true;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to remove'));
      return false;
    }
  }, [fetchSaved]);

  useEffect(() => {
    fetchSaved();
  }, [fetchSaved]);

  return {
    saved,
    loading,
    error,
    saveOpportunity,
    removeSaved,
    refresh: fetchSaved
  };
};
3. Database Standards
3.1 SQL Standards
-- Table naming: lowercase, underscores, plural
CREATE TABLE users (
    -- Primary key: table name + _id
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Descriptive column names
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Boolean columns: descriptive names
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    
    -- Foreign keys: table_name_id
    organization_id UUID REFERENCES organizations(organization_id),
    
    -- Check constraints
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Index naming: idx_table_name_column
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_organization_id ON users(organization_id);

-- Comment tables and columns
COMMENT ON TABLE users IS 'User accounts and authentication';
COMMENT ON COLUMN users.email IS 'User email address for login and notifications';

-- Always use transactions
BEGIN;
    UPDATE users SET email = 'new@example.com' WHERE user_id = '123';
    INSERT INTO audit_logs (user_id, action) VALUES ('123', 'email_update');
COMMIT;
3.2 SQLAlchemy Models
# models.py
from typing import Optional, List
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime,
    ForeignKey, Text, JSON, Enum, ARRAY, Float
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import uuid

from database import Base

class User(Base):
    __tablename__ = "users"
    
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(100)
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now()
    )
    
    # Relationships
    profile: Mapped["UserProfile"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    searches: Mapped[List["SearchHistory"]] = relationship(
        back_populates="user"
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "user_id": str(self.user_id),
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat()
        }

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        unique=True
    )
    country: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    skills: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    preferences: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="profile")
