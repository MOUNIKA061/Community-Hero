import os
import json
import tempfile
import logging
from pydantic import BaseModel, Field
import google.generativeai as genai

logger = logging.getLogger(__name__)


class AIRecommendation(BaseModel):
    recommended_action: str = Field(description="Specific, actionable repair/resolution step for municipal workers. E.g. 'Repair using cold-mix asphalt patching and re-stripe lane markings.'")
    estimated_completion: str = Field(description="Realistic estimated time to resolve. E.g. '2-3 hours', '1 working day', '3-5 days'.")
    resources_needed: list[str] = Field(description="List of physical resources and personnel needed. E.g. ['2 Road Workers', '1 Asphalt Truck', '50kg Cold-mix Asphalt'].")
    risk_if_delayed: str = Field(description="Description of risks or harms if the issue is not resolved promptly. E.g. 'Vehicle damage, risk of accidents and traffic congestion.'")
    priority_score: str = Field(description="Overall resolution priority. Must be exactly one of: Critical, High, Medium, Low.")


class IssueAnalysis(BaseModel):
    category: str = Field(description="Must be exactly one of: Pothole, Garbage Dump, Water Leakage, Damaged Streetlight, Road Damage, Other")
    severity: str = Field(description="Must be exactly one of: Low, Medium, High")
    description: str = Field(description="A concise, professional description summarizing the civic issue observed in the media.")
    department: str = Field(description="Responsible municipal department. E.g. Road Maintenance, Sanitation, Water Supply, Electrical Department")
    ai_recommendation: AIRecommendation = Field(description="AI Municipal Officer recommendation for resolving this issue.")


def analyze_media(file_bytes: bytes, mime_type: str, filename: str) -> dict:
    """
    Analyzes an image or video using the Google Gemini API.
    Returns structured analysis including category, severity, description, department,
    and an AI Municipal Officer recommendation.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable is not configured.")
        raise ValueError("GEMINI_API_KEY environment variable is required for Gemini AI analysis.")
        
    model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
    
    # Configure Gemini SDK
    genai.configure(api_key=api_key)
    
    ext = os.path.splitext(filename)[1]
    temp_path = None
    gemini_file = None
    
    try:
        # 1. Write the file bytes to a local temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name
            
        logger.info("Uploading file to Gemini File API: %s (%s)", filename, mime_type)
        gemini_file = genai.upload_file(path=temp_path, mime_type=mime_type)
        logger.info("Gemini File API upload complete. Remote identifier: %s", gemini_file.name)
        
        # 2. Build prompt for issue identification and AI Municipal Officer recommendations
        prompt = (
            "You are an AI Municipal Officer analyzing a community-reported civic issue. "
            "Analyze the provided media carefully and return a structured JSON response.\n\n"
            "For identification:\n"
            "- category: Must be one of: Pothole, Garbage Dump, Water Leakage, Damaged Streetlight, Road Damage, Other\n"
            "- severity: Must be one of: Low, Medium, High\n"
            "- description: A concise, professional description of the problem for public viewing\n"
            "- department: The responsible municipal department (e.g. Road Maintenance, Sanitation, Water Supply, Electrical Department)\n\n"
            "For ai_recommendation (act as a senior municipal officer giving actionable guidance):\n"
            "- recommended_action: A specific, step-by-step action the department should take to resolve this\n"
            "- estimated_completion: A realistic time estimate for full resolution\n"
            "- resources_needed: A list of personnel and materials needed\n"
            "- risk_if_delayed: What harm could occur if this is not fixed promptly\n"
            "- priority_score: Must be one of: Critical, High, Medium, Low"
        )
        
        # 3. Instantiate model and generation config with response schema
        model = genai.GenerativeModel(model_name)
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=IssueAnalysis,
            temperature=0.2
        )
        
        logger.info("Requesting generation from Gemini model: %s", model_name)
        response = model.generate_content(
            [gemini_file, prompt],
            generation_config=generation_config
        )
        
        logger.info("Gemini generation successful.")
        result = json.loads(response.text)
        return result
        
    except Exception as e:
        logger.error("Failed to analyze media content with Gemini API: %s", e)
        raise RuntimeError(f"Failed to analyze media content with Gemini API: {e}")
        
    finally:
        # 4. Perform cleanups of temporary resources
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info("Cleaned up local temporary file: %s", temp_path)
            except Exception as cleanup_err:
                logger.warning("Failed to delete local temp file %s: %s", temp_path, cleanup_err)
                
        if gemini_file:
            try:
                genai.delete_file(gemini_file.name)
                logger.info("Cleaned up remote Gemini File API resource: %s", gemini_file.name)
            except Exception as delete_err:
                logger.warning("Failed to delete remote Gemini file %s: %s", gemini_file.name, delete_err)
