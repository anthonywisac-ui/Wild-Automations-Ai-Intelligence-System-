WEBSITE ARCHITECTURE

1. Website Overview
1.1 Architecture Components
┌─────────────────────────────────────────────────────────────────────────────┐
│                      WEBSITE ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    FRONTEND APPLICATION                               │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │    React    │  │   Next.js   │  │   Redux     │  │   React   │  │  │
│  │  │   Core      │  │   Framework │  │   State     │  │   Router  │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    UI COMPONENTS                                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Material   │  │  Tailwind   │  │  Framer     │  │  React    │  │  │
│  │  │  UI         │  │  CSS        │  │  Motion     │  │  Hook     │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    FEATURES MODULES                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Dashboard  │  │   Search    │  │   Profile   │  │   Admin   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Notify     │  │   Analytics │  │   Settings  │  │   Help    │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    STATE MANAGEMENT                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │   Redux     │  │   RTK       │  │   Context   │  │   React   │  │  │
│  │  │   Store     │  │   Query     │  │   API       │  │   Query   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    BACKEND INTEGRATION                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │   REST API  │  │  WebSocket  │  │   GraphQL   │  │   SWR     │  │  │
│  │  │   Client    │  │   Client    │  │   Client    │  │   Hooks   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

2. Frontend Stack
2.1 Technology Stack
Component	Technology	Version	Purpose
Framework	Next.js	14.0+	React framework with SSR
Language	TypeScript	5.0+	Type-safe JavaScript
Styling	Tailwind CSS	3.0+	Utility-first CSS
UI Library	Material-UI	5.0+	Component library
State Management	Redux Toolkit	1.9+	Global state management
Data Fetching	RTK Query	1.9+	API integration
Routing	Next.js Router	14.0+	File-based routing
Forms	React Hook Form	7.0+	Form management
Validation	Zod	3.0+	Schema validation
Animations	Framer Motion	10.0+	Animation library
Charts	Recharts	2.0+	Data visualization
Testing	Jest + React Testing Library	29.0+	Unit and integration testing
2.2 Project Structure
text
wildautomations-web/
├── public/
│   ├── images/
│   ├── icons/
│   └── fonts/
├── src/
│   ├── app/
│   │   ├── api/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   └── forgot-password/
│   │   ├── (dashboard)/
│   │   │   ├── dashboard/
│   │   │   ├── search/
│   │   │   ├── opportunities/
│   │   │   ├── notifications/
│   │   │   └── profile/
│   │   ├── (admin)/
│   │   │   ├── admin/
│   │   │   ├── sources/
│   │   │   ├── users/
│   │   │   └── analytics/
│   │   └── layout.tsx
│   ├── components/
│   │   ├── common/
│   │   │   ├── Layout/
│   │   │   ├── Navigation/
│   │   │   ├── Footer/
│   │   │   └── Loading/
│   │   ├── auth/
│   │   │   ├── LoginForm/
│   │   │   ├── RegisterForm/
│   │   │   └── SocialLogin/
│   │   ├── dashboard/
│   │   │   ├── OpportunityCard/
│   │   │   ├── SearchBar/
│   │   │   ├── FilterPanel/
│   │   │   └── Statistics/
│   │   ├── opportunities/
│   │   │   ├── OpportunityDetail/
│   │   │   ├── OpportunityList/
│   │   │   └── OpportunitySaver/
│   │   └── admin/
│   │       ├── SourceManager/
│   │       ├── UserManager/
│   │       └── MetricsDashboard/
│   ├── store/
│   │   ├── slices/
│   │   ├── api/
│   │   └── hooks/
│   ├── hooks/
│   │   ├── useAuth/
│   │   ├── useSearch/
│   │   └── useNotifications/
│   ├── utils/
│   │   ├── api/
│   │   ├── validation/
│   │   └── helpers/
│   ├── types/
│   │   ├── api/
│   │   └── models/
│   └── styles/
│       ├── globals.css
│       └── tailwind.css
├── tests/
│   ├── unit/
│   └── integration/
├── package.json
├── next.config.js
├── tailwind.config.js
└── tsconfig.json
3. Core Features Implementation
3.1 Authentication
typescript
// src/hooks/useAuth.ts
import { useDispatch, useSelector } from 'react-redux'
import { useRouter } from 'next/navigation'
import { useState, useEffect } from 'react'
import { loginUser, registerUser, logoutUser } from '@/store/slices/authSlice'

export const useAuth = () => {
  const dispatch = useDispatch()
  const router = useRouter()
  const { user, token, isLoading, error } = useSelector((state) => state.auth)
  
  const login = async (email: string, password: string) => {
    try {
      const result = await dispatch(loginUser({ email, password })).unwrap()
      router.push('/dashboard')
      return result
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  }
  
  const register = async (userData: RegisterData) => {
    try {
      const result = await dispatch(registerUser(userData)).unwrap()
      router.push('/login?registered=true')
      return result
    } catch (error) {
      console.error('Registration failed:', error)
      throw error
    }
  }
  
  const logout = async () => {
    await dispatch(logoutUser())
    router.push('/login')
  }
  
  return {
    user,
    token,
    isLoading,
    error,
    login,
    register,
    logout,
    isAuthenticated: !!token && !!user
  }
}
3.2 Search Implementation
typescript
// src/components/dashboard/SearchBar.tsx
import { useState, useCallback } from 'react'
import { useSearch } from '@/hooks/useSearch'
import { useDebounce } from '@/hooks/useDebounce'
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Clear as ClearIcon
} from '@mui/icons-material'

export const SearchBar = () => {
  const [query, setQuery] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const debouncedQuery = useDebounce(query, 300)
  const { search, results, isLoading, filters, setFilters, clearFilters } = useSearch()
  
  const handleSearch = useCallback((value: string) => {
    setQuery(value)
    search({ query: value, filters })
  }, [search, filters])
  
  const handleFilterChange = useCallback((newFilters: FilterType) => {
    setFilters(newFilters)
    search({ query, filters: newFilters })
  }, [search, query])
  
  return (
    <div className="search-container">
      <div className="search-input-wrapper">
        <SearchIcon className="search-icon" />
        <input
          type="text"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          placeholder="Search opportunities..."
          className="search-input"
        />
        {query && (
          <button onClick={() => handleSearch('')} className="clear-btn">
            <ClearIcon />
          </button>
        )}
        <button onClick={() => setShowFilters(!showFilters)} className="filter-btn">
          <FilterIcon />
        </button>
      </div>
      
      {showFilters && (
        <FilterPanel
          filters={filters}
          onChange={handleFilterChange}
          onClear={clearFilters}
        />
      )}
      
      {isLoading && <LoadingSpinner />}
      
      <SearchResults
        results={results}
        isLoading={isLoading}
      />
    </div>
  )
}
3.3 Dashboard Layout
typescript
// src/app/(dashboard)/dashboard/page.tsx
import { Metadata } from 'next'
import { DashboardStats } from '@/components/dashboard/DashboardStats'
import { RecentOpportunities } from '@/components/dashboard/RecentOpportunities'
import { SavedSearches } from '@/components/dashboard/SavedSearches'
import { NotificationCenter } from '@/components/dashboard/NotificationCenter'
import { QuickActions } from '@/components/dashboard/QuickActions'

export const metadata: Metadata = {
  title: 'Dashboard - WildAutomations',
  description: 'Your personalized opportunity dashboard'
}

export default function DashboardPage() {
  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>Welcome back, User!</h1>
        <div className="dashboard-actions">
          <QuickActions />
        </div>
      </header>
      
      <section className="dashboard-stats">
        <DashboardStats />
      </section>
      
      <div className="dashboard-grid">
        <div className="main-content">
          <section className="recent-opportunities">
            <h2>Recent Opportunities</h2>
            <RecentOpportunities />
          </section>
          
          <section className="saved-searches">
            <h2>Saved Searches</h2>
            <SavedSearches />
          </section>
        </div>
        
        <aside className="sidebar">
          <section className="notifications">
            <h2>Notifications</h2>
            <NotificationCenter />
          </section>
          
          <section className="quick-links">
            <h2>Quick Links</h2>
            <QuickLinks />
          </section>
        </aside>
      </div>
    </div>
  )
}
4. State Management
4.1 Redux Store Configuration
typescript
// src/store/index.ts
import { configureStore } from '@reduxjs/toolkit'
import { setupListeners } from '@reduxjs/toolkit/query'
import { authApi } from './api/authApi'
import { opportunitiesApi } from './api/opportunitiesApi'
import { searchApi } from './api/searchApi'
import authReducer from './slices/authSlice'
import searchReducer from './slices/searchSlice'
import notificationReducer from './slices/notificationSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    search: searchReducer,
    notifications: notificationReducer,
    [authApi.reducerPath]: authApi.reducer,
    [opportunitiesApi.reducerPath]: opportunitiesApi.reducer,
    [searchApi.reducerPath]: searchApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware()
      .concat(authApi.middleware)
      .concat(opportunitiesApi.middleware)
      .concat(searchApi.middleware)
})

setupListeners(store.dispatch)

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
4.2 API Integration
typescript
// src/store/api/opportunitiesApi.ts
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import { RootState } from '@/store'

export const opportunitiesApi = createApi({
  reducerPath: 'opportunitiesApi',
  baseQuery: fetchBaseQuery({
    baseUrl: process.env.NEXT_PUBLIC_API_URL,
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as RootState).auth.token
      if (token) {
        headers.set('authorization', `Bearer ${token}`)
      }
      return headers
    }
  }),
  tagTypes: ['Opportunity', 'SavedOpportunity'],
  endpoints: (builder) => ({
    searchOpportunities: builder.query<SearchResponse, SearchRequest>({
      query: (params) => ({
        url: '/search',
        method: 'POST',
        body: params
      }),
      providesTags: ['Opportunity']
    }),
    
    getOpportunityById: builder.query<Opportunity, string>({
      query: (id) => `/opportunities/${id}`,
      providesTags: (result, error, id) => [{ type: 'Opportunity', id }]
    }),
    
    saveOpportunity: builder.mutation<void, string>({
      query: (id) => ({
        url: '/opportunities/save',
        method: 'POST',
        body: { opportunity_id: id }
      }),
      invalidatesTags: ['SavedOpportunity']
    }),
    
    getSavedOpportunities: builder.query<Opportunity[], void>({
      query: () => '/opportunities/saved',
      providesTags: ['SavedOpportunity']
    }),
    
    removeSavedOpportunity: builder.mutation<void, string>({
      query: (id) => ({
        url: `/opportunities/save/${id}`,
        method: 'DELETE'
      }),
      invalidatesTags: ['SavedOpportunity']
    })
  })
})

export const {
  useSearchOpportunitiesQuery,
  useGetOpportunityByIdQuery,
  useSaveOpportunityMutation,
  useGetSavedOpportunitiesQuery,
  useRemoveSavedOpportunityMutation
} = opportunitiesApi
5. Responsive Design
5.1 Breakpoints
css
/* src/styles/tailwind.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --breakpoint-sm: 640px;
    --breakpoint-md: 768px;
    --breakpoint-lg: 1024px;
    --breakpoint-xl: 1280px;
    --breakpoint-2xl: 1536px;
  }
}

/* Responsive Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  
  @media (min-width: 768px) {
    grid-template-columns: 2fr 1fr;
  }
  
  @media (min-width: 1024px) {
    gap: 2rem;
  }
}

/* Responsive Search */
.search-container {
  width: 100%;
  
  @media (min-width: 768px) {
    max-width: 600px;
  }
  
  @media (min-width: 1024px) {
    max-width: 800px;
  }
}
5.2 Mobile Navigation
typescript
// src/components/common/Navigation/MobileNav.tsx
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Menu as MenuIcon,
  Close as CloseIcon,
  Home,
  Search,
  Notifications,
  Person,
  Settings,
  Logout
} from '@mui/icons-material'

export const MobileNav = () => {
  const [isOpen, setIsOpen] = useState(false)
  const router = useRouter()
  
  const navItems = [
    { icon: Home, label: 'Dashboard', path: '/dashboard' },
    { icon: Search, label: 'Search', path: '/search' },
    { icon: Notifications, label: 'Notifications', path: '/notifications' },
    { icon: Person, label: 'Profile', path: '/profile' },
    { icon: Settings, label: 'Settings', path: '/settings' }
  ]
  
  return (
    <>
      <button
        className="mobile-menu-toggle"
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <CloseIcon /> : <MenuIcon />}
      </button>
      
      {isOpen && (
        <div className="mobile-menu-overlay">
          <nav className="mobile-menu">
            {navItems.map((item) => (
              <button
                key={item.path}
                className="mobile-nav-item"
                onClick={() => {
                  router.push(item.path)
                  setIsOpen(false)
                }}
              >
                <item.icon />
                <span>{item.label}</span>
              </button>
            ))}
            <button className="mobile-nav-item logout" onClick={() => {}}>
              <Logout />
              <span>Logout</span>
            </button>
          </nav>
        </div>
      )}
    </>
  )
}
6. Performance Optimization
6.1 Image Optimization
typescript
// src/components/common/Image.tsx
import NextImage from 'next/image'
import { useState } from 'react'

interface ImageProps {
  src: string
  alt: string
  width?: number
  height?: number
  className?: string
  priority?: boolean
}

export const Image = ({
  src,
  alt,
  width,
  height,
  className,
  priority = false
}: ImageProps) => {
  const [isLoading, setIsLoading] = useState(true)
  
  return (
    <div className={`image-container ${className}`}>
      <NextImage
        src={src}
        alt={alt}
        width={width}
        height={height}
        priority={priority}
        className={`
          transition-opacity duration-300
          ${isLoading ? 'opacity-0' : 'opacity-100'}
        `}
        onLoadingComplete={() => setIsLoading(false)}
        sizes="
          (max-width: 768px) 100vw,
          (max-width: 1200px) 50vw,
          33vw
        "
      />
      {isLoading && <div className="image-placeholder" />}
    </div>
  )
}
6.2 Code Splitting
typescript
// src/app/(dashboard)/dashboard/page.tsx
import dynamic from 'next/dynamic'
import { Suspense } from 'react'

// Lazy load heavy components
const DashboardStats = dynamic(
  () => import('@/components/dashboard/DashboardStats'),
  { loading: () => <LoadingSpinner /> }
)

const RecentOpportunities = dynamic(
  () => import('@/components/dashboard/RecentOpportunities'),
  { loading: () => <LoadingSpinner /> }
)

const SavedSearches = dynamic(
  () => import('@/components/dashboard/SavedSearches'),
  { loading: () => <LoadingSpinner /> }
)

export default function DashboardPage() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <div className="dashboard-container">
        <DashboardStats />
        <div className="dashboard-grid">
          <RecentOpportunities />
          <SavedSearches />
        </div>
      </div>
    </Suspense>
  )
}


