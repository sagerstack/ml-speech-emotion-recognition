# Streamlit Antd Components Documentation

## Overview
Streamlit Antd Components is a custom component library that implements Antd-Design and Mantine widgets for Streamlit applications. It provides 17 modern UI components with enhanced styling and functionality.

## Installation
```bash
pip install streamlit-antd-components
```

**Requirements:**
- Python >= 3.8
- Streamlit

## Quick Start
```python
import streamlit as st
import streamlit_antd_components as sac

# Basic button example
btn = sac.buttons(
    items=['button1', 'button2', 'button3'],
    index=0,
    format_func='title',
    align='center',
    direction='horizontal',
    radius='lg',
    return_index=False,
)
st.write(f'The selected button label is: {btn}')
```

## Available Components

### 1. buttons
Creates a group of buttons with customizable styling.

**Parameters:**
- `items` (list): List of button labels
- `index` (int): Initial selected button index (default: 0)
- `format_func` (str/function): Function to format button labels (default: 'title')
- `align` (str): Alignment option ('center', 'left', 'right')
- `direction` (str): Button layout ('horizontal', 'vertical')
- `radius` (str): Button border radius ('sm', 'md', 'lg', 'xl')
- `return_index` (bool): Return index instead of label (default: False)

**Example:**
```python
selected = sac.buttons(
    items=['Home', 'Profile', 'Settings'],
    index=0,
    align='center',
    direction='horizontal',
    radius='md'
)
```

### 2. divider
Creates a visual separator line between content sections.

**Parameters:**
- `content` (str): Optional text to display on the divider
- `variant` (str): Divider style ('solid', 'dashed', 'dotted')
- `orientation` (str): Text orientation ('left', 'center', 'right')

**Example:**
```python
sac.divider("Section Break", orientation="center")
```

### 3. menu
Creates a navigation menu with hierarchical structure.

**Parameters:**
- `items` (list): Menu items configuration
- `index` (int): Selected menu index
- `open_index` (list): Indices of expanded submenu items
- `mode` (str): Menu mode ('vertical', 'horizontal', 'inline')
- `theme` (str): Menu theme ('light', 'dark')

**Example:**
```python
menu_items = [
    {"title": "File", "icon": "file"},
    {"title": "Edit", "icon": "edit"},
    {"title": "View", "icon": "eye"}
]
selected_menu = sac.menu(items=menu_items, index=0, mode="vertical")
```

### 4. steps
Creates a step-by-step progress indicator.

**Parameters:**
- `items` (list): Step items with titles and descriptions
- `current` (int): Current step index
- `direction` (str): Step direction ('horizontal', 'vertical')
- `status` (str): Step status ('wait', 'process', 'finish', 'error')

**Example:**
```python
step_items = [
    {"title": "Upload", "description": "Upload audio file"},
    {"title": "Process", "description": "Analyze emotion"},
    {"title": "Results", "description": "View results"}
]
current_step = sac.steps(items=step_items, current=1)
```

### 5. cascader
Creates a cascading selection component for hierarchical data.

**Parameters:**
- `items` (list): Hierarchical data structure
- `placeholder` (str): Input placeholder text
- `multiple` (bool): Allow multiple selections
- `show_search` (bool): Enable search functionality

**Example:**
```python
cascade_data = [
    {
        "label": "Audio",
        "value": "audio",
        "children": [
            {"label": "WAV", "value": "wav"},
            {"label": "MP3", "value": "mp3"}
        ]
    }
]
selected = sac.cascader(items=cascade_data, placeholder="Select format")
```

### 6. checkbox
Creates a checkbox group for multiple selections.

**Parameters:**
- `items` (list): Checkbox options
- `index` (list): Selected checkbox indices
- `inline` (bool): Display checkboxes inline

**Example:**
```python
emotions = ['Happy', 'Sad', 'Angry', 'Neutral']
selected_emotions = sac.checkbox(items=emotions, index=[0, 3])
```

### 7. rate
Creates a star rating component.

**Parameters:**
- `value` (float): Initial rating value
- `count` (int): Number of stars (default: 5)
- `allow_half` (bool): Allow half-star ratings
- `readonly` (bool): Make component read-only

**Example:**
```python
rating = sac.rate(value=4.5, allow_half=True)
```

### 8. switch
Creates a toggle switch component.

**Parameters:**
- `value` (bool): Initial switch state
- `label` (str): Switch label text
- `disabled` (bool): Disable the switch

**Example:**
```python
enabled = sac.switch(value=True, label="Enable notifications")
```

### 9. transfer
Creates a double-column transfer component for moving items between lists.

**Parameters:**
- `items` (list): Transfer items
- `target_keys` (list): Initially selected target items
- `titles` (list): Column titles
- `show_search` (bool): Enable search in both columns

**Example:**
```python
transfer_items = [
    {"key": "1", "title": "Happy"},
    {"key": "2", "title": "Sad"},
    {"key": "3", "title": "Angry"}
]
selected_targets = sac.transfer(
    items=transfer_items,
    target_keys=["1", "3"],
    titles=["Available", "Selected"]
)
```

### 10. segmented
Creates segmented control for single selection.

**Parameters:**
- `items` (list): Segment options
- `index` (int): Selected segment index
- `size` (str): Component size ('small', 'middle', 'large')

**Example:**
```python
emotion_levels = ['Low', 'Medium', 'High']
selected_level = sac.segmented(items=emotion_levels, index=1)
```

### 11. tabs
Creates tabbed navigation interface.

**Parameters:**
- `items` (list): Tab items with labels and content
- `index` (int): Active tab index
- `position` (str): Tab position ('top', 'right', 'bottom', 'left')
- `type` (str): Tab style ('line', 'card', 'editable-card')

**Example:**
```python
tab_items = [
    {"label": "Upload", "children": "Upload content here"},
    {"label": "Analyze", "children": "Analysis content here"},
    {"label": "Results", "children": "Results content here"}
]
active_tab = sac.tabs(items=tab_items, index=0)
```

### 12. tree
Creates hierarchical tree structure component.

**Parameters:**
- `items` (list): Tree data structure
- `checked_keys` (list): Checked item keys
- `selected_keys` (list): Selected item keys
- `expand_keys` (list): Expanded node keys
- `checkable` (bool): Enable checkboxes
- `show_search` (bool): Enable search functionality

**Example:**
```python
tree_data = [
    {
        "title": "Audio Files",
        "key": "audio",
        "children": [
            {"title": "speech.wav", "key": "speech"},
            {"title": "interview.mp3", "key": "interview"}
        ]
    }
]
selected_items = sac.tree(items=tree_data, selected_keys=["speech"])
```

### 13. alert
Creates alert message components.

**Parameters:**
- `type` (str): Alert type ('success', 'info', 'warning', 'error')
- `message` (str): Alert message
- `description` (str): Optional detailed description
- `closable` (bool): Allow closing the alert
- `show_icon` (bool): Show alert icon

**Example:**
```python
sac.alert(
    type="success",
    message="Analysis Complete",
    description="Emotion detection finished successfully"
)
```

### 14. result
Creates result display component for task completion.

**Parameters:**
- `status` (str): Result status ('success', 'error', 'info', 'warning', '404', '403', '500')
- `title` (str): Result title
- `sub_title` (str): Result subtitle
- `extra` (list): Additional action buttons

**Example:**
```python
sac.result(
    status="success",
    title="Emotion Detected",
    sub_title="Primary emotion: Happy (85% confidence)"
)
```

### 15. tag
Creates categorization tags.

**Parameters:**
- `items` (list): Tag items with labels and colors
- `closable` (bool): Allow closing tags
- `color` (str): Tag color

**Example:**
```python
tags = [
    {"label": "Happy", "color": "green"},
    {"label": "Confident", "color": "blue"}
]
sac.tag(items=tags, closable=True)
```

### 16. pagination
Creates pagination component.

**Parameters:**
- `total` (int): Total number of items
- `current` (int): Current page
- `page_size` (int): Items per page
- `show_size_changer` (bool): Allow changing page size
- `show_quick_jumper` (bool): Show quick page jump

**Example:**
```python
current_page = sac.pagination(
    total=100,
    current=1,
    page_size=10,
    show_size_changer=True
)
```

## Styling and Customization

### Common Styling Options
Most components support these common styling parameters:
- `size`: Component size ('small', 'middle', 'large')
- `disabled`: Disable component interaction
- `style`: Custom CSS styles
- `className`: Custom CSS classes

### Theme Support
Components support light and dark themes through the `theme` parameter where applicable.

## Best Practices

1. **Consistent Naming**: Use meaningful variable names for component instances
2. **State Management**: Store component values in Streamlit session state for persistence
3. **Layout**: Use Streamlit columns and containers for proper component layout
4. **Performance**: Avoid excessive component updates within loops

## Integration Example

Here's a complete example for an emotion analysis interface:

```python
import streamlit as st
import streamlit_antd_components as sac

# Initialize session state
if 'current_step' not in st.session_state:
    st.session_state.current_step = 0
if 'selected_emotions' not in st.session_state:
    st.session_state.selected_emotions = []

# Page title
st.title("Emotion Analysis Interface")

# Progress steps
steps = [
    {"title": "Upload", "description": "Upload audio file"},
    {"title": "Configure", "description": "Set analysis options"},
    {"title": "Analyze", "description": "Process audio"},
    {"title": "Results", "description": "View results"}
]

sac.steps(items=steps, current=st.session_state.current_step)

# Content based on current step
if st.session_state.current_step == 0:
    st.subheader("Upload Audio File")
    uploaded_file = st.file_uploader("Choose audio file", type=['wav', 'mp3'])

    if uploaded_file:
        if sac.button("Next", key="upload_next"):
            st.session_state.current_step += 1
            st.rerun()

elif st.session_state.current_step == 1:
    st.subheader("Configure Analysis")

    # Emotion selection
    emotions = ['Happy', 'Sad', 'Angry', 'Fear', 'Surprise', 'Disgust', 'Neutral']
    selected = sac.checkbox(
        items=emotions,
        index=[0, 6],  # Default: Happy and Neutral
        title="Select emotions to detect"
    )

    # Sensitivity slider
    sensitivity = sac.rate(
        value=3,
        count=5,
        title="Analysis Sensitivity"
    )

    col1, col2 = st.columns(2)
    with col1:
        if sac.button("Previous", key="config_prev"):
            st.session_state.current_step -= 1
            st.rerun()
    with col2:
        if sac.button("Analyze", key="analyze_btn"):
            st.session_state.current_step += 1
            st.rerun()

# Navigation tabs
tabs = [
    {"label": "Analysis", "children": "Main analysis interface"},
    {"label": "History", "children": "Previous analyses"},
    {"label": "Settings", "children": "Application settings"}
]

selected_tab = sac.tabs(items=tabs, index=0)
```

## Resources and Links

- **PyPI Package**: https://pypi.org/project/streamlit-antd-components/
- **GitHub Repository**: https://github.com/nicedouble/StreamlitAntdComponents
- **Live Demo**: https://nicedouble-streamlitantdcomponentsdemo-app-middmy.streamlit.app/
- **Current Version**: 0.3.2 (Released January 19, 2024)

## License

This library is open source. Check the repository for specific license information.

## Troubleshooting

### Common Issues

1. **Import Error**: Ensure you have the correct package name `streamlit_antd_components`
2. **Component Not Rendering**: Check Streamlit version compatibility
3. **Styling Issues**: Verify CSS is not conflicting with existing styles

### Getting Help

- Check the GitHub repository for known issues
- Visit the demo app for working examples
- Review Streamlit community forums