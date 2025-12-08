#!/bin/bash
#
# Set ml-ser-deploy as the default AWS profile
#

set -e

PROFILE_NAME="ml-ser-deploy"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setting $PROFILE_NAME as Default AWS Profile"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if profile exists
if ! aws configure list-profiles | grep -q "^${PROFILE_NAME}$"; then
  echo "❌ Error: Profile '$PROFILE_NAME' not found"
  echo ""
  echo "Available profiles:"
  aws configure list-profiles
  exit 1
fi

echo "Found profile: $PROFILE_NAME"
echo ""

# Backup existing files
echo "📦 Creating backups..."
cp ~/.aws/credentials ~/.aws/credentials.backup.$(date +%Y%m%d_%H%M%S)
cp ~/.aws/config ~/.aws/config.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backups created"
echo ""

# Option selection
echo "Choose method to set as default:"
echo "  1) Environment variable (recommended for temporary)"
echo "  2) Rename profile to [default] (permanent)"
echo ""
read -p "Select option (1 or 2): " -n 1 -r
echo
echo ""

if [[ $REPLY == "1" ]]; then
  # Option 1: Environment variable
  echo "Setting environment variable..."

  # Detect shell
  if [ -n "$ZSH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
    SHELL_NAME="zsh"
  elif [ -n "$BASH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
    SHELL_NAME="bash"
  else
    SHELL_CONFIG="$HOME/.profile"
    SHELL_NAME="shell"
  fi

  # Check if already set
  if grep -q "AWS_PROFILE=${PROFILE_NAME}" "$SHELL_CONFIG" 2>/dev/null; then
    echo "⚠️  AWS_PROFILE already set in $SHELL_CONFIG"
  else
    echo "" >> "$SHELL_CONFIG"
    echo "# AWS Default Profile" >> "$SHELL_CONFIG"
    echo "export AWS_PROFILE=${PROFILE_NAME}" >> "$SHELL_CONFIG"
    echo "✅ Added to $SHELL_CONFIG"
  fi

  # Set for current session
  export AWS_PROFILE=${PROFILE_NAME}
  echo "✅ Set for current session"
  echo ""
  echo "To apply in new terminals, run:"
  echo "  source $SHELL_CONFIG"

elif [[ $REPLY == "2" ]]; then
  # Option 2: Rename to [default]
  echo "Renaming profile to [default]..."

  # Get credentials for ml-ser-deploy
  ACCESS_KEY=$(aws configure get aws_access_key_id --profile ${PROFILE_NAME})
  SECRET_KEY=$(aws configure get aws_secret_access_key --profile ${PROFILE_NAME})
  REGION=$(aws configure get region --profile ${PROFILE_NAME} || echo "us-east-1")
  OUTPUT=$(aws configure get output --profile ${PROFILE_NAME} || echo "json")

  # Set as default
  aws configure set aws_access_key_id "$ACCESS_KEY"
  aws configure set aws_secret_access_key "$SECRET_KEY"
  aws configure set region "$REGION"
  aws configure set output "$OUTPUT"

  echo "✅ Profile set as [default]"
  echo ""
  echo "Note: The [${PROFILE_NAME}] profile still exists."
  echo "You can remove it if you want:"
  echo "  sed -i '' '/\[${PROFILE_NAME}\]/,/^$/d' ~/.aws/credentials"
  echo "  sed -i '' '/\[profile ${PROFILE_NAME}\]/,/^$/d' ~/.aws/config"

else
  echo "❌ Invalid option"
  exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Verify
echo "Current AWS identity:"
aws sts get-caller-identity

echo ""
echo "✅ Setup complete!"
echo ""

if [[ $REPLY == "1" ]]; then
  echo "AWS_PROFILE is now set to: $PROFILE_NAME"
  echo ""
  echo "To use in new terminals:"
  echo "  source $SHELL_CONFIG"
fi

echo ""
echo "Test with:"
echo "  aws sts get-caller-identity"
echo ""
