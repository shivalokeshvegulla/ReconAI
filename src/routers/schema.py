from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.schema import SchemaManifest

router = APIRouter(tags=["Schema"])

@router.get("/schema/manifest", response_model=SchemaManifest)
def get_schema_manifest(db: Session = Depends(get_db)):
    #Inside the function, query the database for the latest schema record 
    record = db.scalar(
    select(SchemaManifestDB)
    .order_by(SchemaManifestDB.id.desc())
    .limit(1)
    )
    query = db.scalar(record)
    if query is None:
        raise HTTPException(status_code=404, detail="Schema manifest not found")
    # Convert it back to the Pydantic schema
    manifest = SchemaManifest.model_validate(
    record,
    from_attributes=True
    )

return manifest

@router.post("/schema/manifest", response_model=SchemaManifest)
def update_schema_manifest(manifest: SchemaManifest, db: Session = Depends(get_db)):

    data = manifest.model_dump()
    records = db.scalars(select(ManifestDB)).all()
    for record in records:
        db.delete(record)
    new_record = SchemaManifestDB(**data)
    try:
        db.add(new_record)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update schema manifest: {str(e)}")
    
    db.refresh(new_record)
    # Convert it back to the Pydantic schema
    saved_manifest = SchemaManifest.model_validate(
    new_record,
    from_attributes=True)

return saved_manifest