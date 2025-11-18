import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  Container,
  Typography,
  Box,
  Paper,
} from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

// Create a theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function Dashboard() {
  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        ML Speech Emotion Recognition Dashboard
      </Typography>

      <Typography variant="body1" color="text.secondary" paragraph>
        Real-time monitoring dashboard for speech emotion recognition API
      </Typography>

      {/* Dashboard Grid Layout */}
      <Box
        sx={{
          display: 'grid',
          gap: 3,
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        }}
      >
        {/* System Health Card */}
        <Paper
          sx={{ p: 3, display: 'flex', flexDirection: 'column', height: 240 }}
        >
          <Typography variant="h6" component="h2">
            System Health
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Backend API Status:{' '}
            <span style={{ color: 'green' }}>● Healthy</span>
          </Typography>
          <Typography variant="body2" color="text.secondary">
            SageMaker Endpoint:{' '}
            <span style={{ color: 'green' }}>● Connected</span>
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Uptime: 99.9%
          </Typography>
        </Paper>

        {/* Request Metrics Card */}
        <Paper
          sx={{ p: 3, display: 'flex', flexDirection: 'column', height: 240 }}
        >
          <Typography variant="h6" component="h2">
            Request Metrics
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Requests/Minute: 45
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Avg Response Time: 1.2s
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Error Rate: 0.1%
          </Typography>
        </Paper>

        {/* Active Connections Card */}
        <Paper
          sx={{ p: 3, display: 'flex', flexDirection: 'column', height: 240 }}
        >
          <Typography variant="h6" component="h2">
            WebSocket Connections
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Active Connections: 12
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Total Processed: 1,247
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Success Rate: 99.5%
          </Typography>
        </Paper>
      </Box>

      {/* Charts Section */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="h5" component="h2" gutterBottom>
          Performance Overview
        </Typography>
        <Paper sx={{ p: 3, height: 400 }}>
          <Typography variant="body1" color="text.secondary">
            Charts and detailed metrics will be implemented here.
            <br />
            Integration with backend API for real-time monitoring data.
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <div className="App">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/dashboard" element={<Dashboard />} />
            </Routes>
          </div>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
