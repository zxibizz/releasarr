# Media Request Tracker - Frontend Prototype

A React TypeScript frontend prototype for tracking and managing media server requests, built as part of the Releasarr project.

## Features

- **Request Management**: View and filter media requests (movies and TV series)
- **Detailed Request Pages**: Individual pages for each request with comprehensive media information
- **Torrent Search**: Integrated torrent search functionality with mock data
- **Responsive Design**: Clean, dark-themed interface optimized for media management
- **Type Safety**: Full TypeScript implementation with comprehensive type definitions

## Architecture

### Components
- `RequestsList`: Main page displaying all requests with filtering capabilities
- `RequestPage`: Detailed view for individual requests
- `RequestCard`: Reusable card component for request list items
- `MediaInfo`: Component for displaying detailed media information
- `TorrentSearch`: Integrated torrent search with results display

### Data Management
- **Custom Hooks**: `useRequests` and `useTorrentSearch` for state management
- **Mock Data Service**: Comprehensive mock data for development and testing
- **API Service Layer**: Prepared for easy backend integration

### Types
- Comprehensive TypeScript interfaces for all data structures
- Support for both movie and series requests
- Torrent search result types

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm start
   ```

3. Open [http://localhost:3000](http://localhost:3000) to view the application

## Project Structure

```
src/
├── components/          # React components
│   ├── RequestsList.tsx
│   ├── RequestPage.tsx
│   ├── RequestCard.tsx
│   ├── MediaInfo.tsx
│   └── TorrentSearch.tsx
├── hooks/              # Custom React hooks
│   ├── useRequests.ts
│   └── useTorrentSearch.ts
├── services/           # Data services
│   ├── mockData.ts
│   └── api.ts
├── types/              # TypeScript type definitions
│   └── index.ts
├── utils/              # Utility functions
│   └── formatters.ts
└── App.tsx            # Main application component
```

## Mock Data

The application includes comprehensive mock data featuring:
- 4 movie requests with various statuses
- 4 TV series requests (season-based)
- Sample torrent search results
- Realistic media metadata (posters, descriptions, genres)

## Features Implemented

### Request Filtering
- Filter by status (pending, searching, downloading, completed, failed)
- Filter by type (movies, series)
- View all requests

### Request Details
- Comprehensive media information display
- Status tracking with visual indicators
- Genre tags and metadata
- IMDb integration links
- Series-specific information (season, episodes)

### Torrent Search
- Search form with query input
- Results display with quality indicators
- Seeder/leecher information
- File size and source information
- Mock torrent selection functionality

### User Experience
- Loading states for all async operations
- Error handling with user-friendly messages
- Responsive design for various screen sizes
- Dark theme optimized for media management

## Backend Integration Ready

The application is structured for easy backend integration:
- API service layer with proper error handling
- Consistent data fetching patterns
- Environment-based configuration
- Prepared endpoints for CRUD operations

## Development Notes

- Built with Create React App and TypeScript
- Uses modern React patterns (functional components, hooks)
- Comprehensive error handling and loading states
- Prepared for TailwindCSS integration (currently using basic CSS)
- ESLint configured for code quality

## Next Steps

1. **Backend Integration**: Connect to actual Releasarr API endpoints
2. **Enhanced Styling**: Complete TailwindCSS integration for better UI
3. **Real-time Updates**: WebSocket integration for live status updates
4. **User Authentication**: Add user management and permissions
5. **Advanced Filtering**: More sophisticated search and filter options
6. **Notifications**: Toast notifications for user actions
7. **Testing**: Comprehensive unit and integration tests

## Technologies Used

- React 18
- TypeScript
- React Router DOM
- Date-fns for date formatting
- Clsx for conditional styling
- Modern ES6+ features

This prototype demonstrates a complete media request management system with a clean, intuitive interface and robust architecture ready for production deployment.
