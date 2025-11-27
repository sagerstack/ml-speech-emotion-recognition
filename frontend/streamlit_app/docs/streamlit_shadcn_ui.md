# Streamlit ShadCN UI Documentation

## Overview
Streamlit ShadCN UI is a comprehensive library that brings modern shadcn-ui components to Streamlit applications. Built with React and Tailwind CSS, it provides accessible, customizable UI components with a clean design system.

## Installation
```bash
pip install streamlit-shadcn-ui
```

**Requirements:**
- Python >= 3.7
- Streamlit
- Modern web browser for React components

## Quick Start
```python
import streamlit as st
import streamlit_shadcn_ui as ui

# Basic button and dialog example
trigger_btn = ui.button(text="Trigger Button", key="trigger_btn")
ui.alert_dialog(
    show=trigger_btn,
    title="Alert Dialog",
    description="This is an alert dialog",
    confirm_label="OK",
    cancel_label="Cancel",
    key="alert_dialog1"
)
```

## Component Categories

### 🎯 Core Form Components

#### button
Interactive button with various styles and configurations.

**Parameters:**
- `text` (str): Button text
- `variant` (str): Button style ('default', 'destructive', 'outline', 'secondary', 'ghost', 'link')
- `size` (str): Button size ('default', 'sm', 'lg', 'icon')
- `disabled` (bool): Disable button
- `loading` (bool): Show loading state
- `key` (str): Unique component key

**Example:**
```python
primary_btn = ui.button("Submit", variant="default", size="lg", key="submit")
outline_btn = ui.button("Cancel", variant="outline", key="cancel")
danger_btn = ui.button("Delete", variant="destructive", key="delete")
```

#### input
Text input field with various input types and validation.

**Parameters:**
- `placeholder` (str): Input placeholder text
- `type` (str): Input type ('text', 'password', 'email', 'number')
- `value` (str): Initial value
- `disabled` (bool): Disable input
- `required` (bool): Mark as required
- `max_length` (int): Maximum character length
- `key` (str): Unique component key

**Example:**
```python
username = ui.input(
    placeholder="Enter username",
    type="text",
    required=True,
    key="username_input"
)
password = ui.input(
    placeholder="Enter password",
    type="password",
    key="password_input"
)
```

#### textarea
Multi-line text input for longer content.

**Parameters:**
- `placeholder` (str): Placeholder text
- `value` (str): Initial text content
- `rows` (int): Number of visible rows
- `max_length` (int): Maximum character length
- `disabled` (bool): Disable textarea
- `key` (str): Unique component key

**Example:**
```python
notes = ui.textarea(
    placeholder="Enter your notes here...",
    rows=4,
    max_length=500,
    key="notes_area"
)
```

#### select
Dropdown selection component with search functionality.

**Parameters:**
- `placeholder` (str): Placeholder text
- `options` (list): List of selectable options
- `value` (str): Selected value
- `multiple` (bool): Allow multiple selections
- `searchable` (bool): Enable search
- `disabled` (bool): Disable select
- `key` (str): Unique component key

**Example:**
```python
emotion = ui.select(
    placeholder="Select emotion",
    options=["Happy", "Sad", "Angry", "Neutral", "Surprise"],
    value="Neutral",
    searchable=True,
    key="emotion_select"
)
```

#### checkbox
Checkbox input for boolean selections.

**Parameters:**
- `label` (str): Checkbox label
- `checked` (bool): Initial checked state
- `disabled` (bool): Disable checkbox
- `key` (str): Unique component key

**Example:**
```python
agree_terms = ui.checkbox(
    label="I agree to the terms and conditions",
    checked=False,
    key="terms_checkbox"
)
```

#### radio_group
Radio button group for single selection from multiple options.

**Parameters:**
- `options` (list): List of radio options
- `value` (str): Selected value
- `orientation` (str): Button layout ('horizontal', 'vertical')
- `disabled` (bool): Disable radio group
- `key` (str): Unique component key

**Example:**
```python
priority = ui.radio_group(
    options=["Low", "Medium", "High"],
    value="Medium",
    orientation="horizontal",
    key="priority_radio"
)
```

#### switch
Toggle switch for binary on/off selections.

**Parameters:**
- `label` (str): Switch label
- `checked` (bool): Initial checked state
- `disabled` (bool): Disable switch
- `key` (str): Unique component key

**Example:**
```python
notifications = ui.switch(
    label="Enable notifications",
    checked=True,
    key="notifications_switch"
)
```

#### slider
Range slider for numerical value selection.

**Parameters:**
- `min` (float): Minimum value
- `max` (float): Maximum value
- `step` (float): Step increment
- `value` (float/list): Current value or range
- `disabled` (bool): Disable slider
- `key` (str): Unique component key

**Example:**
```python
confidence = ui.slider(
    min=0.0,
    max=1.0,
    step=0.1,
    value=0.8,
    key="confidence_slider"
)
```

### 🎨 Layout & Display Components

#### card
Card container for organizing related content.

**Parameters:**
- `title` (str): Card title
- `description` (str): Card description
- `footer` (str): Card footer content
- `variant` (str): Card style ('default', 'outline')
- `key` (str): Unique component key

**Example:**
```python
with ui.card(title="Analysis Results", key="results_card"):
    st.write("Primary emotion: Happy")
    st.write("Confidence: 92%")
```

#### accordion
Collapsible content sections for organizing information.

**Parameters:**
- `items` (list): List of accordion sections with title and content
- `type` (str): Accordion style ('single', 'multiple')
- `default_value` (str/list): Default open section(s)
- `collapsible` (bool): Allow collapsing all sections
- `key` (str): Unique component key

**Example:**
```python
accordion_items = [
    {
        "title": "Audio Details",
        "content": "Duration: 3:45, Sample rate: 44.1kHz"
    },
    {
        "title": "Analysis Method",
        "content": "Used deep learning model with 95% accuracy"
    }
]
ui.accordion(items=accordion_items, type="multiple", key="details_accordion")
```

#### tabs
Tabbed navigation for organizing content into sections.

**Parameters:**
- `items` (list): List of tab items with labels and content
- `default_value` (str): Default active tab
- `orientation` (str): Tab orientation ('horizontal', 'vertical')
- `key` (str): Unique component key

**Example:**
```python
tab_items = [
    {"label": "Upload", "content": "Upload your audio files here"},
    {"label": "Analyze", "content": "Configure analysis settings"},
    {"label": "Results", "content": "View analysis results"}
]
ui.tabs(items=tab_items, default_value="Upload", key="main_tabs")
```

#### collapsible
Expandable/collapsible container for content.

**Parameters:**
- `title` (str): Collapsible title
- `open` (bool): Initial open state
- `disabled` (bool): Disable collapsing
- `key` (str): Unique component key

**Example:**
```python
with ui.collapsible(title="Advanced Settings", open=False, key="advanced_settings"):
    st.write("Configure advanced analysis parameters")
```

### 🔔 Feedback Components

#### alert
Alert message components for status notifications.

**Parameters:**
- `title` (str): Alert title
- `description` (str): Alert description
- `variant` (str): Alert type ('default', 'destructive', 'warning', 'success')
- `show_icon` (bool): Display alert icon

**Example:**
```python
ui.alert(
    title="Success!",
    description="Analysis completed successfully",
    variant="success",
    show_icon=True
)
```

#### alert_dialog
Modal dialog for user confirmation or information.

**Parameters:**
- `show` (bool): Control dialog visibility
- `title` (str): Dialog title
- `description` (str): Dialog description
- `confirm_label` (str): Confirm button text
- `cancel_label` (str): Cancel button text
- `key` (str): Unique component key

**Example:**
```python
show_dialog = ui.button("Show Confirmation", key="show_dialog")
ui.alert_dialog(
    show=show_dialog,
    title="Confirm Action",
    description="Are you sure you want to proceed with the analysis?",
    confirm_label="Yes, Analyze",
    cancel_label="Cancel",
    key="confirm_dialog"
)
```

#### dialog
Modal dialog component for complex interactions.

**Parameters:**
- `show` (bool): Control dialog visibility
- `title` (str): Dialog title
- `description` (str): Dialog description
- `confirm_label` (str): Confirm button text
- `cancel_label` (str): Cancel button text
- `key` (str): Unique component key

**Example:**
```python
show_settings = ui.button("Open Settings", key="open_settings")
ui.dialog(
    show=show_settings,
    title="Analysis Settings",
    description="Configure your emotion analysis parameters",
    confirm_label="Save Settings",
    cancel_label="Cancel",
    key="settings_dialog"
)
```

#### progress
Progress bar component for showing completion status.

**Parameters:**
- `value` (float): Progress percentage (0-100)
- `max_value` (float): Maximum value (default: 100)
- `variant` (str): Progress style ('default', 'success', 'warning', 'destructive')
- `key` (str): Unique component key

**Example:**
```python
ui.progress(
    value=75,
    variant="default",
    key="upload_progress"
)
```

### 📊 Data Display Components

#### table
Data table for displaying structured information.

**Parameters:**
- `data` (list/dict): Table data
- `columns` (list): Column definitions
- `searchable` (bool): Enable search functionality
- `sortable` (bool): Enable column sorting
- `pagination` (bool): Enable table pagination
- `key` (str): Unique component key

**Example:**
```python
table_data = [
    {"emotion": "Happy", "confidence": 0.92, "timestamp": "2024-01-15 10:30"},
    {"emotion": "Neutral", "confidence": 0.85, "timestamp": "2024-01-15 10:35"},
    {"emotion": "Sad", "confidence": 0.78, "timestamp": "2024-01-15 10:40"}
]
ui.table(data=table_data, searchable=True, sortable=True, key="results_table")
```

#### metric_card
Metric display card for key performance indicators.

**Parameters:**
- `title` (str): Metric title
- `value` (str/number): Metric value
- `description` (str): Metric description
- `trend` (str): Trend direction ('up', 'down', 'neutral')
- `key` (str): Unique component key

**Example:**
```python
ui.metric_card(
    title="Analysis Accuracy",
    value="94.2%",
    description="↑ 2.1% from last week",
    trend="up",
    key="accuracy_metric"
)
```

#### avatar
User avatar component for displaying profile images.

**Parameters:**
- `src` (str): Image URL or path
- `alt` (str): Alternative text
- `size` (str): Avatar size ('sm', 'md', 'lg', 'xl')
- `fallback` (str): Fallback text for missing image
- `key` (str): Unique component key

**Example:**
```python
ui.avatar(
    src="https://example.com/avatar.jpg",
    alt="User Avatar",
    size="md",
    fallback="JD",
    key="user_avatar"
)
```

### 📅 Date/Time Components

#### date_picker
Date selection component.

**Parameters:**
- `placeholder` (str): Placeholder text
- `value` (str): Selected date
- `disabled` (bool): Disable date picker
- `key` (str): Unique component key

**Example:**
```python
selected_date = ui.date_picker(
    placeholder="Select analysis date",
    key="date_picker"
)
```

#### date_range_picker
Date range selection component.

**Parameters:**
- `placeholder` (str): Placeholder text
- `value` (list): Selected date range [start, end]
- `disabled` (bool): Disable date range picker
- `key` (str): Unique component key

**Example:**
```python
date_range = ui.date_range_picker(
    placeholder="Select date range",
    key="range_picker"
)
```

#### calendar
Interactive calendar component.

**Parameters:**
- `selected` (str): Selected date
- `disabled` (bool): Disable calendar
- `key` (str): Unique component key

**Example:**
```python
selected_calendar_date = ui.calendar(
    key="calendar_picker"
)
```

### 🎛️ Navigation & Interaction Components

#### dropdown_menu
Context menu for additional actions.

**Parameters:**
- `trigger` (str): Menu trigger element
- `items` (list): Menu items with labels and actions
- `side` (str): Menu position ('top', 'right', 'bottom', 'left')
- `key` (str): Unique component key

**Example:**
```python
menu_trigger = ui.button("More Options", key="menu_trigger")
ui.dropdown_menu(
    trigger=menu_trigger,
    items=[
        {"label": "Export Results", "value": "export"},
        {"label": "Share Analysis", "value": "share"},
        {"label": "Delete", "value": "delete"}
    ],
    key="options_menu"
)
```

#### hover_card
Card that appears on hover for additional information.

**Parameters:**
- `trigger` (str): Element that triggers hover
- `content` (str): Hover card content
- `side` (str): Hover position ('top', 'right', 'bottom', 'left')
- `key` (str): Unique component key

**Example:**
```python
info_trigger = ui.button("ℹ️ Info", key="info_trigger")
ui.hover_card(
    trigger=info_trigger,
    content="This analysis uses a deep learning model trained on CREMA-D dataset",
    key="info_hover"
)
```

#### popover
Popover component for additional context.

**Parameters:**
- `trigger` (str): Element that triggers popover
- `content` (str): Popover content
- `side` (str): Popover position
- `key` (str): Unique component key

**Example:**
```python
settings_trigger = ui.button("⚙️ Settings", key="settings_trigger")
ui.popover(
    trigger=settings_trigger,
    content="Configure analysis parameters and model settings",
    key="settings_popover"
)
```

## Advanced Features

### Nested Components (Experimental)
The library supports nesting components within a single iframe for better performance:

```python
with ui.card(key="outer_card"):
    st.write("This is the outer card")

    with ui.card(key="inner_card"):
        ui.element("input", key="nested_input", placeholder="Nested input")
        ui.element("button", key="nested_btn", text="Nested Submit", variant="outline")

    ui.element("button", key="outer_btn", text="Outer Button")
```

### Dynamic Element Creation
Use `ui.element()` for dynamic component creation:

```python
# Create components dynamically
component_type = "button"
ui.element(
    component_type,
    key="dynamic_btn",
    text="Dynamic Button",
    variant="outline"
)
```

## Styling and Theming

### Custom CSS
Apply custom styles using the `style` parameter:

```python
ui.button(
    text="Styled Button",
    key="styled_btn",
    style={"backgroundColor": "#3b82f6", "color": "white"}
)
```

### Theme Support
Components automatically adapt to Streamlit's theme settings. Light and dark modes are supported.

## Integration Example

Here's a complete emotion analysis interface using various shadcn-ui components:

```python
import streamlit as st
import streamlit_shadcn_ui as ui

# Page header
st.title("🎭 Emotion Analysis Dashboard")

# Initialize session state
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False

# Upload section
with ui.card(title="Audio Upload", key="upload_card"):
    uploaded_file = st.file_uploader(
        "Choose audio file",
        type=['wav', 'mp3', 'm4a'],
        key="file_uploader"
    )

    if uploaded_file:
        ui.alert(
            title="File Uploaded",
            description=f"File: {uploaded_file.name} ({uploaded_file.size} bytes)",
            variant="success"
        )

# Configuration section
with ui.card(title="Analysis Configuration", key="config_card"):
    col1, col2 = st.columns(2)

    with col1:
        # Emotion selection
        emotion = ui.select(
            placeholder="Select target emotion",
            options=["Happy", "Sad", "Angry", "Neutral", "Surprise", "Fear", "Disgust"],
            key="emotion_select"
        )

        # Sensitivity slider
        sensitivity = ui.slider(
            min=0.1,
            max=1.0,
            step=0.1,
            value=0.8,
            key="sensitivity_slider"
        )

    with col2:
        # Additional options
        include_timestamp = ui.checkbox(
            label="Include timestamp analysis",
            checked=True,
            key="timestamp_check"
        )

        use_gpu = ui.switch(
            label="Use GPU acceleration",
            checked=False,
            key="gpu_switch"
        )

# Analysis triggers
col1, col2, col3 = st.columns(3)

with col1:
    analyze_btn = ui.button(
        text="🚀 Start Analysis",
        variant="default",
        size="lg",
        key="analyze_btn"
    )

with col2:
    reset_btn = ui.button(
        text="🔄 Reset",
        variant="outline",
        key="reset_btn"
    )

with col3:
    help_btn = ui.button(
        text="❓ Help",
        variant="ghost",
        key="help_btn"
    )

# Help dialog
ui.alert_dialog(
    show=help_btn,
    title="Analysis Help",
    description="This tool analyzes audio files to detect emotions using machine learning. Upload a file, configure settings, and click 'Start Analysis'.",
    confirm_label="Got it!",
    cancel_label="Cancel",
    key="help_dialog"
)

# Results section (shown after analysis)
if st.session_state.analysis_complete:
    st.markdown("---")

    # Metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        ui.metric_card(
            title="Primary Emotion",
            value="Happy",
            description="92% confidence",
            trend="up",
            key="primary_emotion"
        )

    with col2:
        ui.metric_card(
            title="Processing Time",
            value="2.3s",
            description="Below average",
            trend="down",
            key="processing_time"
        )

    with col3:
        ui.metric_card(
            title="Accuracy",
            value="94.7%",
            description="+1.2% improvement",
            trend="up",
            key="accuracy"
        )

    # Detailed results
    with ui.card(title="Detailed Analysis", key="results_card"):
        # Results table
        results_data = [
            {"emotion": "Happy", "confidence": 0.92, "duration": "0:00 - 0:45"},
            {"emotion": "Neutral", "confidence": 0.05, "duration": "0:45 - 1:20"},
            {"emotion": "Surprise", "confidence": 0.03, "duration": "1:20 - 1:45"}
        ]

        ui.table(
            data=results_data,
            searchable=True,
            key="results_table"
        )

    # Progress tracking
    ui.progress(
        value=100,
        variant="success",
        key="analysis_progress"
    )

    # Export options
    with ui.card(title="Export Options", key="export_card"):
        export_menu = ui.button("📥 Export Results", key="export_btn")

        ui.dropdown_menu(
            trigger=export_menu,
            items=[
                {"label": "Export as CSV", "value": "csv"},
                {"label": "Export as JSON", "value": "json"},
                {"label": "Generate Report", "value": "report"}
            ],
            key="export_menu"
        )

# Settings configuration
with ui.collapsible(title="Advanced Settings", open=False, key="advanced_settings"):
    st.write("Configure advanced analysis parameters")

    model_params = ui.radio_group(
        options=["Lightweight", "Standard", "High Precision"],
        value="Standard",
        key="model_params"
    )

    batch_size = ui.input(
        placeholder="Batch size",
        type="number",
        value="32",
        key="batch_size_input"
    )

# Footer
st.markdown("---")
with ui.card(key="footer_card"):
    st.markdown("**Emotion Analysis Dashboard** - Built with Streamlit and shadcn-ui")
```

## Resources and Links

- **Live Demo & Documentation**: https://shadcn.streamlit.app/
- **GitHub Repository**: https://github.com/ObservedObserver/streamlit-shadcn-ui
- **shadcn/ui Official**: https://ui.shadcn.com/
- **Component Gallery**: Available in the live demo app

## Development

### Local Development
For local development and contribution:

```bash
# Clone the repository
git clone https://github.com/ObservedObserver/streamlit-shadcn-ui.git

# Frontend development
./scripts/frontend.sh

# Streamlit development
./scripts/dev.sh
```

### Project Structure
- `./streamlit_shadcn_ui`: Python package
- Frontend: React-based shadcn components
- Built on shadcn/ui component library

## Best Practices

1. **Component Keys**: Always use unique keys for component instances
2. **State Management**: Use Streamlit session state for data persistence
3. **Performance**: Minimize unnecessary component re-renders
4. **Accessibility**: Leverage built-in accessibility features
5. **Responsive Design**: Test components on different screen sizes

## Troubleshooting

### Common Issues

1. **Component Not Rendering**: Check component key uniqueness
2. **Import Errors**: Verify package installation: `pip install streamlit-shadcn-ui`
3. **Styling Conflicts**: Check for CSS conflicts with existing styles
4. **Performance Issues**: Use nested components for complex layouts

### Getting Help

- Visit the live demo app for working examples
- Check the GitHub repository for known issues
- Review Streamlit community discussions

## License

MIT License - see LICENSE file in the repository for details.