from services.ai_service import predict_recovery
import json

# Test prediction for ACC004
result = predict_recovery('ACC004', None)

print("Prediction Result:")
print(json.dumps(result, indent=2, default=str))
