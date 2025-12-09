"""
WSGI Application for SageMaker Inference

This module provides the Flask application that handles:
- /ping: Health check endpoint
- /invocations: Inference endpoint

It delegates to inference.py from the model's code/ directory for
model-specific loading and prediction logic.
"""

import os
import sys
import json
import logging
import traceback

import flask

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Model directory where SageMaker mounts the model artifacts
MODEL_DIR = os.environ.get('MODEL_DIR', '/opt/ml/model')

# Add code directory to path for inference.py and custom classes
code_dir = os.path.join(MODEL_DIR, 'code')
if os.path.exists(code_dir) and code_dir not in sys.path:
    sys.path.insert(0, code_dir)
    logger.info(f"Added {code_dir} to Python path")

# Import inference functions from the model's code directory
# These are model-version-specific and packaged with the model tarball
try:
    from inference import model_fn, input_fn, predict_fn, output_fn
    logger.info("Successfully imported inference functions from model code directory")
except ImportError as e:
    logger.error(f"Failed to import inference.py from {code_dir}: {e}")
    raise

# Flask app
app = flask.Flask(__name__)

# Global model variable (cached after first load)
_model = None


def get_model():
    """Load and cache the model using inference.py's model_fn."""
    global _model

    if _model is not None:
        return _model

    logger.info(f"Loading model from {MODEL_DIR}")
    _model = model_fn(MODEL_DIR)
    logger.info("Model loaded and cached successfully")
    return _model


@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint."""
    try:
        # Try to load model to verify it works
        get_model()
        status = 200
        response = {'status': 'healthy'}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        status = 500
        response = {'status': 'unhealthy', 'error': str(e)}

    return flask.Response(
        response=json.dumps(response),
        status=status,
        mimetype='application/json'
    )


@app.route('/invocations', methods=['POST'])
def invocations():
    """Inference endpoint using inference.py functions."""
    try:
        # Get model
        model = get_model()

        # Get request data
        content_type = flask.request.content_type or 'application/json'
        request_body = flask.request.get_data(as_text=True)

        # Use inference.py functions for model-specific logic
        # 1. Parse input
        input_data = input_fn(request_body, content_type)

        # 2. Run prediction
        prediction_result = predict_fn(input_data, model)

        # 3. Format output
        accept = flask.request.headers.get('Accept', 'application/json')
        response_body = output_fn(prediction_result, accept)

        logger.info(f"Prediction successful")

        return flask.Response(
            response=response_body,
            status=200,
            mimetype='application/json'
        )

    except ValueError as e:
        # Input validation errors
        logger.error(f"Input error: {e}")
        return flask.Response(
            response=json.dumps({'error': str(e)}),
            status=400,
            mimetype='application/json'
        )

    except Exception as e:
        logger.error(f"Inference failed: {e}")
        logger.error(traceback.format_exc())
        return flask.Response(
            response=json.dumps({'error': str(e)}),
            status=500,
            mimetype='application/json'
        )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
