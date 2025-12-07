"""
WSGI Application for SageMaker Inference

This module provides the Flask application that handles:
- /ping: Health check endpoint
- /invocations: Inference endpoint
"""

import os
import sys
import json
import pickle
import logging
import traceback

import flask
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Model directory where SageMaker mounts the model artifacts
MODEL_DIR = os.environ.get('MODEL_DIR', '/opt/ml/model')

# Flask app
app = flask.Flask(__name__)

# Global model variable
model = None


def load_model():
    """Load the model from the model directory."""
    global model

    if model is not None:
        return model

    model_path = os.path.join(MODEL_DIR, 'model.pkl')

    # Add code directory to path for custom classes
    code_dir = os.path.join(MODEL_DIR, 'code')
    if os.path.exists(code_dir) and code_dir not in sys.path:
        sys.path.insert(0, code_dir)
        logger.info(f"Added {code_dir} to Python path")

    # Import custom classes and inject into __main__ for pickle compatibility
    # The model was pickled with UltraEnsembleModel in __main__, so we need
    # to make it available there for unpickling to work
    try:
        from ultra_ensemble import UltraEnsembleModel
        import __main__
        __main__.UltraEnsembleModel = UltraEnsembleModel
        logger.info("Imported and injected UltraEnsembleModel into __main__")
    except ImportError:
        logger.warning("UltraEnsembleModel not found in code directory")

    logger.info(f"Loading model from {model_path}")

    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        logger.info("Model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        logger.error(traceback.format_exc())
        raise


@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint."""
    try:
        # Try to load model to verify it works
        load_model()
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
    """Inference endpoint."""
    try:
        # Load model
        model = load_model()

        # Get input data
        content_type = flask.request.content_type or 'application/json'

        if 'application/json' in content_type:
            input_data = flask.request.get_json()
        elif 'application/x-npy' in content_type:
            # Handle numpy array input
            input_data = np.load(flask.request.stream)
        else:
            return flask.Response(
                response=json.dumps({'error': f'Unsupported content type: {content_type}'}),
                status=415,
                mimetype='application/json'
            )

        # Extract features from input
        if isinstance(input_data, dict):
            if 'features' in input_data:
                features = np.array(input_data['features'])
            elif 'instances' in input_data:
                features = np.array(input_data['instances'])
            else:
                features = np.array(input_data.get('data', input_data))
        else:
            features = np.array(input_data)

        # Ensure 2D array
        if features.ndim == 1:
            features = features.reshape(1, -1)

        logger.info(f"Received input with shape: {features.shape}")

        # Make prediction
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(features)
            predictions = model.predict(features)

            # Get class labels if available
            if hasattr(model, 'classes_'):
                classes = model.classes_.tolist()
            else:
                classes = list(range(probabilities.shape[1]))

            result = {
                'predictions': predictions.tolist(),
                'probabilities': probabilities.tolist(),
                'classes': classes
            }
        else:
            predictions = model.predict(features)
            result = {
                'predictions': predictions.tolist()
            }

        logger.info(f"Prediction successful: {result['predictions']}")

        return flask.Response(
            response=json.dumps(result),
            status=200,
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
