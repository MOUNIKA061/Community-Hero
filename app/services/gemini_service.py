import os
import json
import tempfile
import logging
from pydantic import BaseModel, Field
import google.generativeai as genai

logger = logging.getLogger(__name__)

class IssueAnalysis(BaseModel):
    category: str = Field(description="Must be exactly one of: Pothole, Garbage Dump, Water Leakage, Damaged Streetlight, Road Damage, Other")
    severity: str = Field(description="Must be exactly one of: Low, Medium, High")
    description: str = Field(description="A concise, professional description summarizing the civic issue observed in the media.")
    department: str = Field(description="Responsible municipal department. E.g. Road Maintenance, Sanitation, Water Supply, Electrical Department")


def analyze_media(file_bytes: bytes, mime_type: str, filename: str) -> dict:
    """
    Analyzes an image or video using the Google Gemini API.
    Returns structured analysis details containing category, severity, description, and department.
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
        
        # 2. Build prompt for issue identification
        prompt = (
            "Analyze this community issue media. Provide structured analysis parameters. "
            "The category must be one of: Pothole, Garbage Dump, Water Leakage, Damaged Streetlight, Road Damage, Other. "
            "The severity must be one of: Low, Medium, High. "
            "Determine the correct municipal department to assign. "
            "Write a clear, description of the problem for public viewing."
        )
        
        # 3. Instantiate model and generation config with response schema
        model = genai.GenerativeModel(model_name)
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=IssueAnalysis,
            temperature=0.1
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
