#!/usr/bin/env python3
"""
PLUMATOTM Animal × Planet Scoring System - HTTP API Server

This FastAPI server exposes the astrological analysis engine as a REST API
for integration with Shopify and other web applications.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Dict, Any, Optional
import uvicorn
import json
import os
from datetime import datetime
from contextlib import suppress

# Import our existing analysis engine
from plumatotm_core import BirthChartAnalyzer, convert_local_to_utc

# Import radar chart generator
from plumatotm_radar import RadarChartGenerator

# Optional: OpenAI client for explanations
with suppress(ImportError):
    from openai import OpenAI  # type: ignore
    OPENAI_AVAILABLE = True
else:
    OPENAI_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI(
    title="PLUMATOTM Astrological Analysis API",
    description="API for computing animal scores based on birth chart data",
    version="1.0.0"
)

# Add CORS middleware for web integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize the analyzer with our data files
try:
    analyzer = BirthChartAnalyzer(
        "plumatotm_raw_scores.json",
        "plumatotm_planets_weights.csv", 
        "plumatotm_planets_multiplier.csv"
    )
    print("✅ Analysis engine initialized successfully")
except Exception as e:
    print(f"❌ Error initializing analysis engine: {e}")
    analyzer = None

# Initialize radar chart generator
try:
    radar_generator = RadarChartGenerator()
    print("✅ Radar chart generator initialized successfully")
except Exception as e:
    print(f"❌ Error initializing radar chart generator: {e}")
    radar_generator = None

# Pydantic models for request/response validation
class BirthDataRequest(BaseModel):
    date: str  # YYYY-MM-DD
    time: str  # HH:MM (24h format)
    lat: float
    lon: float
    name: Optional[str] = None  # Optional name for reference
    
    @validator('date')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')
    
    @validator('time')
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
            return v
        except ValueError:
            raise ValueError('Time must be in HH:MM format (24h)')
    
    @validator('lat')
    def validate_lat(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('lon')
    def validate_lon(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v

class AnalysisResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def _generate_top_animal_explanation(top_animal: Dict[str, Any], context: Dict[str, Any]) -> str:
    """
    Generate a short explanation for the top animal using OpenAI if available.
    Falls back to a deterministic text if OpenAI is not configured.
    """
    # Basic fallback if SDK or key not available
    if not OPENAI_AVAILABLE or not OPENAI_API_KEY:
        name = str(top_animal.get("ANIMAL", "Animal"))
        score = top_animal.get("TOTAL_SCORE")
        return (
            f"{name}: votre animal totem principal. Ce profil ressort en première position "
            f"avec un score {score}. Il symbolise votre énergie dominante et vos qualités "
            f"naturelles."
        )

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        animal_name = str(top_animal.get("ANIMAL", "Animal"))
        score = top_animal.get("TOTAL_SCORE")
        percentages = context.get("top3_percentage_strength", {})
        planets = context.get("birth_chart", {}).get("planets", {})

        system_prompt = (
            "Tu es un expert en symbolique animale et astrologie moderne. "
            "Tu écris des explications courtes, positives, concrètes. "
            "Ton ton est bienveillant, clair, sans jargon inutile. "
            "Langue: français. Longueur: ~120-180 mots."
        )
        user_prompt = (
            "Concisément, explique l'animal totem qui ressort en 1ère position.\n"
            f"- Animal: {animal_name}\n"
            f"- Score total: {score}\n"
            f"- Pourcentages forces (top3): {percentages}\n"
            f"- Indices planétaires (si utiles): {list(planets.keys())[:5]}\n"
            "Structure attendue: 2-3 phrases sur l'essence, 1-2 sur les forces, 1 sur les conseils."
        )

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return completion.choices[0].message.content or ""
    except Exception:
        # Silent fallback
        name = str(top_animal.get("ANIMAL", "Animal"))
        return (
            f"{name}: votre animal totem principal. Il met en lumière vos atouts naturels "
            f"et la direction la plus porteuse pour vous en ce moment."
        )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "PLUMATOTM Astrological Analysis API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "analyzer_ready": analyzer is not None,
        "radar_generator_ready": radar_generator is not None,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_birth_data(request: BirthDataRequest):
    """
    Analyze birth data and return animal scores
    
    This endpoint takes birth date, time, and coordinates,
    computes the astrological chart, and returns the top animal matches.
    """
    
    if analyzer is None:
        raise HTTPException(status_code=500, detail="Analysis engine not available")
    
    try:
        # Convert local time to UTC
        utc_time = convert_local_to_utc(request.date, request.time, request.lat, request.lon)
        
        # Run the analysis
        analyzer.run_analysis(request.date, utc_time, request.lat, request.lon)
        
        # Read the results from the outputs directory
        with open("outputs/result.json", 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        # Extract top 3 animals for easy access
        animal_totals = results.get("animal_totals", [])
        top_3_animals = animal_totals[:3] if animal_totals else []
        
        # Generate radar charts if generator is available
        radar_charts = {}
        if radar_generator is not None:
            try:
                # Create a temporary result structure for the radar generator
                temp_result_data = {
                    "data": {
                        "top_3_animals": top_3_animals,
                        "top3_percentage_strength": results.get("top3_percentage_strength", {})
                    }
                }
                
                # Generate top animal radar chart
                top_chart_path = radar_generator.generate_top_animal_radar(temp_result_data)
                radar_charts["top_animal_chart"] = top_chart_path
                
            except Exception as e:
                print(f"Warning: Could not generate radar charts: {e}")
                radar_charts = {}
        
        # Create a simplified response for web integration
        response_data = {
            "birth_data": {
                "date": request.date,
                "time": request.time,
                "utc_time": utc_time,
                "lat": request.lat,
                "lon": request.lon,
                "name": request.name
            },
            "birth_chart": results.get("birth_chart", {}),
            "planet_weights": results.get("planet_weights", {}),
            "top_3_animals": top_3_animals,
            "all_animals": animal_totals,
            "analysis_summary": {
                "total_animals_analyzed": len(animal_totals),
                "top_score": top_3_animals[0]["TOTAL_SCORE"] if top_3_animals else 0
            },
            "radar_charts": radar_charts
        }
        
        return AnalysisResponse(
            success=True,
            message="Analysis completed successfully",
            data=response_data
        )
        
    except Exception as e:
        return AnalysisResponse(
            success=False,
            message="Analysis failed",
            error=str(e)
        )


@app.post("/analyze-with-explanation", response_model=AnalysisResponse)
async def analyze_with_explanation(request: BirthDataRequest):
    """
    Analyze birth data and return scores plus a short OpenAI-generated
    explanation for the top animal.
    """
    if analyzer is None:
        raise HTTPException(status_code=500, detail="Analysis engine not available")

    try:
        utc_time = convert_local_to_utc(request.date, request.time, request.lat, request.lon)
        analyzer.run_analysis(request.date, utc_time, request.lat, request.lon)

        with open("outputs/result.json", 'r', encoding='utf-8') as f:
            results = json.load(f)

        animal_totals = results.get("animal_totals", [])
        top_3_animals = animal_totals[:3] if animal_totals else []
        top_animal = top_3_animals[0] if top_3_animals else None

        radar_charts = {}
        if radar_generator is not None:
            with suppress(Exception):
                temp_result_data = {
                    "data": {
                        "top_3_animals": top_3_animals,
                        "top3_percentage_strength": results.get("top3_percentage_strength", {})
                    }
                }
                top_chart_path = radar_generator.generate_top_animal_radar(temp_result_data)
                radar_charts["top_animal_chart"] = top_chart_path

        explanation = None
        if top_animal:
            context = {
                "top3_percentage_strength": results.get("top3_percentage_strength", {}),
                "birth_chart": results.get("birth_chart", {}),
            }
            explanation = _generate_top_animal_explanation(top_animal, context)

        response_data = {
            "birth_data": {
                "date": request.date,
                "time": request.time,
                "utc_time": utc_time,
                "lat": request.lat,
                "lon": request.lon,
                "name": request.name,
            },
            "birth_chart": results.get("birth_chart", {}),
            "planet_weights": results.get("planet_weights", {}),
            "top_3_animals": top_3_animals,
            "all_animals": animal_totals,
            "analysis_summary": {
                "total_animals_analyzed": len(animal_totals),
                "top_score": top_3_animals[0]["TOTAL_SCORE"] if top_3_animals else 0,
            },
            "radar_charts": radar_charts,
            "top_animal_explanation": explanation,
            "explanation_provider": "openai" if OPENAI_AVAILABLE and OPENAI_API_KEY else "local-fallback",
        }

        return AnalysisResponse(
            success=True,
            message="Analysis completed successfully (with explanation)",
            data=response_data,
        )
    except Exception as e:
        return AnalysisResponse(
            success=False,
            message="Analysis with explanation failed",
            error=str(e),
        )

@app.get("/animals")
async def get_available_animals():
    """Get list of all available animals in the system"""
    if analyzer is None:
        raise HTTPException(status_code=500, detail="Analysis engine not available")
    
    return {
        "animals": analyzer.animals,
        "total_count": len(analyzer.animals)
    }

@app.get("/planets")
async def get_supported_planets():
    """Get list of all supported planets/points"""
    if analyzer is None:
        raise HTTPException(status_code=500, detail="Analysis engine not available")
    
    return {
        "planets": analyzer.supported_planets,
        "total_count": len(analyzer.supported_planets)
    }

@app.post("/generate-radar-charts")
async def generate_radar_charts(request: BirthDataRequest):
    """
    Generate radar charts for the given birth data
    
    This endpoint generates radar charts showing the correlation strength
    between the top animal and all planets.
    """
    
    if analyzer is None:
        raise HTTPException(status_code=500, detail="Analysis engine not available")
    
    if radar_generator is None:
        raise HTTPException(status_code=500, detail="Radar chart generator not available")
    
    try:
        # Convert local time to UTC
        utc_time = convert_local_to_utc(request.date, request.time, request.lat, request.lon)
        
        # Run the analysis
        analyzer.run_analysis(request.date, utc_time, request.lat, request.lon)
        
        # Read the results from the outputs directory
        with open("outputs/result.json", 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        # Extract top 3 animals
        animal_totals = results.get("animal_totals", [])
        top_3_animals = animal_totals[:3] if animal_totals else []
        
        # Create result structure for radar generator
        result_data = {
            "data": {
                "top_3_animals": top_3_animals,
                "top3_percentage_strength": results.get("top3_percentage_strength", {})
            }
        }
        
        # Generate radar charts
        top_chart_path = radar_generator.generate_top_animal_radar(result_data)
        
        return {
            "success": True,
            "message": "Radar charts generated successfully",
            "data": {
                "top_animal": top_3_animals[0] if top_3_animals else None,
                "radar_charts": {
                    "top_animal_chart": top_chart_path
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to generate radar charts",
            "error": str(e)
        }

if __name__ == "__main__":
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get("PORT", 8000))
    
    # Run the server
    print("🚀 Starting PLUMATOTM API Server...")
    print(f"📖 API Documentation available at: http://localhost:{port}/docs")
    print(f"🔗 Health check at: http://localhost:{port}/health")
    
    uvicorn.run(
        "plumatotm_api:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info"
    )
