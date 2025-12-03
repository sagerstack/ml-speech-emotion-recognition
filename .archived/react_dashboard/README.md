# ML Emotion Recognition Dashboard

React-based monitoring dashboard for the ML Speech Emotion Recognition API with comprehensive code quality standards.

## 🚀 Features

- **Real-time Monitoring**: System health metrics and WebSocket connection tracking
- **Performance Analytics**: Request/response visualization with Recharts
- **Responsive Design**: Material-UI components with mobile-first approach
- **TypeScript**: Full type safety and IntelliSense support
- **Modern Stack**: React 18+, React Query, Axios, and Socket.io-client

## 📋 Requirements

- Node.js 16+
- npm 8+
- Modern web browser

## 🛠️ Development Setup

### 1. Install Dependencies

```bash
# Clone and navigate to the project
cd frontend/react_dashboard

# Install all dependencies
npm install

# Or using Makefile
make install
```

### 2. Start Development Server

```bash
# Using npm
npm start

# Using Makefile
make run
```

The dashboard will be available at:
- **Application**: http://localhost:3000
- **API Proxy**: http://localhost:8000 (configured in package.json)

## 🔧 Code Quality

### Available Commands

The project includes a Makefile with convenient development commands:

```bash
# Install dependencies
make install

# Run linter
make lint

# Auto-fix linting issues
make lint-fix

# Check code formatting
make format-check

# Format code
make format

# Run TypeScript type checking
make type-check

# Run tests
make test

# Run tests in watch mode
make test-watch

# Build for production
make build

# Run all code quality checks
make quality

# Auto-fix all code quality issues
make quality-fix

# Clean up artifacts
make clean

# Update dependencies
make update

# Check for security vulnerabilities
make audit
```

### npm Scripts

```bash
npm start          # Start development server
npm run build      # Build for production
npm test           # Run tests
npm run lint       # Run ESLint
npm run lint:fix   # Auto-fix ESLint issues
npm run format     # Format code with Prettier
npm run format:check # Check code formatting
npm run type-check  # Run TypeScript type checking
npm run quality    # Run all quality checks
npm run quality:fix # Auto-fix quality issues
```

## 🎯 Code Quality Tools

### 1. **ESLint** - JavaScript/TypeScript Linting

- **Configuration**: `.eslintrc.js`
- **Features**: React, React Hooks, accessibility checks
- **Auto-fixing**: `npm run lint:fix` or `make lint-fix`

### 2. **Prettier** - Code Formatting

- **Configuration**: `.prettierrc`
- **Features**: Consistent code style, line length, quotes
- **Integration**: Works with ESLint via lint-staged

### 3. **TypeScript** - Type Safety

- **Configuration**: `tsconfig.json`
- **Features**: Full type checking, IntelliSense support
- **Strict Mode**: Enabled for better type safety

### 4. **Husky & lint-staged** - Git Hooks

- **Pre-commit**: Automatic linting and formatting on commit
- **Configuration**: Package.json lint-staged section
- **Integration**: Ensures consistent code quality

## 📊 Configuration Files

### ESLint Configuration (.eslintrc.js)
- React and React Hooks rules
- Import ordering and organization
- Accessibility checks (jsx-a11y)
- TypeScript-specific rules
- Custom rules for code consistency

### Prettier Configuration (.prettierrc)
- Semi-colons and trailing commas
- Single quotes and consistent formatting
- 80-character line length
- Tab width: 2 spaces

### TypeScript Configuration (tsconfig.json)
- Strict type checking enabled
- Modern ES target support
- JSX support for React
- Path mapping for cleaner imports

## 🏗️ Project Structure

```
frontend/react_dashboard/
├── public/                  # Static assets
├── src/
│   ├── components/         # Reusable UI components
│   │   ├── common/        # Generic components
│   │   └── charts/        # Chart components
│   ├── pages/             # Dashboard pages
│   │   ├── Dashboard/     # Main dashboard
│   │   └── Health/        # Health monitoring
│   ├── services/          # API and WebSocket services
│   │   ├── api.ts         # API client
│   │   └── websocket.ts   # WebSocket client
│   ├── utils/             # Utility functions
│   ├── types/             # TypeScript type definitions
│   ├── App.tsx            # Main application component
│   ├── index.tsx          # Application entry point
│   └── index.css          # Global styles
├── .eslintrc.js           # ESLint configuration
├── .prettierrc           # Prettier configuration
├── .prettierignore       # Files to ignore for formatting
├── package.json           # Dependencies and scripts
├── Makefile               # Development commands
└── README.md              # This file
```

## 📦 Dependencies

### Core Dependencies
- **React 18.3+**: Modern React with concurrent features
- **TypeScript 4.9+**: Type-safe JavaScript development
- **Material-UI 6.1+**: React component library
- **Recharts**: Data visualization library
- **React Query**: Data fetching and caching
- **Axios**: HTTP client for API requests
- **Socket.io-client**: Real-time WebSocket communication

### Development Dependencies
- **ESLint**: JavaScript and TypeScript linting
- **Prettier**: Code formatting
- **Husky**: Git hooks management
- **lint-staged**: Run linters on staged files
- **@types/react**: TypeScript definitions for React

## 🚀 Build and Deployment

### Development Build

```bash
# Start development server with hot reload
npm start
# or
make run
```

### Production Build

```bash
# Create optimized production build
npm run build
# or
make build
```

### Build Analysis

```bash
# Analyze bundle size (requires webpack-bundle-analyzer)
npm run build && npx bundle-analyzer build/static/js/*.js
```

## 🔍 Testing

### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test -- --watch

# Run tests with coverage
npm run test -- --coverage --watchAll=false
```

### Test Structure

```
tests/
├── components/           # Component tests
├── pages/               # Page tests
├── utils/               # Utility function tests
└── setup.ts             # Test configuration
```

## 📈 Performance

### Optimizations

- **Code Splitting**: Automatic with Create React App
- **Lazy Loading**: Components loaded on demand
- **Tree Shaking**: Dead code elimination
- **Bundle Analysis**: Regular size monitoring

### Performance Metrics

- **Lighthouse**: Integrated audit scores
- **Bundle Size**: Monitored and optimized
- **Load Times**: Optimized with React Query caching
- **Type Safety**: Zero runtime type errors

## 🔐 Security

### Security Measures

- **Dependency Auditing**: `npm audit` for vulnerability scanning
- **XSS Protection**: React's built-in XSS protection
- **Type Safety**: TypeScript prevents many security issues
- **HTTPS Ready**: Production-ready SSL configuration

### Security Best Practices

- Regular dependency updates
- Content Security Policy headers
- Secure WebSocket connections
- Input validation and sanitization

## 🤝 Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run quality checks: `make quality`
5. Run tests: `make test`
6. Fix any issues found
7. Submit a pull request

### Code Standards

- **TypeScript**: All code must be typed
- **ESLint**: Zero linting errors allowed
- **Prettier**: Consistent code formatting
- **Tests**: New features must include tests
- **Documentation**: Update relevant docs

### Pre-commit Process

1. Husky automatically runs lint-staged on commit
2. ESLint fixes are applied automatically
3. Prettier formats the code
4. TypeScript compilation is checked
5. Only quality code passes to the repository

## 📝 License

This project is part of the ML Speech Emotion Recognition system.

## 🆘 Support

For issues and questions:
1. Check the API Documentation: http://localhost:8000/docs
2. Review component examples in the codebase
3. Check build logs for deployment issues
4. Run `make quality` to verify code health