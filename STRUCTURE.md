Project folder structure

root
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   ├── models/
│   ├── repositories/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   │   ├── feature_extractor_service.py
│   │   ├── kdtree_service.py
│   │   ├── search_service.py
│   │   ├── audio_import_service.py
│   │   ├── audio_management_service.py
│   │   ├── segment_service.py
│   │   └── __init__.py
│   ├── utils/
│   └── static/
│       └── uploads/

├── bird_images/
├── bird_sounds_only/
├── test_soundscapes/
├── train_audio/

├── audio_kdtree.pkl
├── audio_scaler.pkl

├── bird_search_pipeline.py
├── extract_features.py
├── master_importer.py
├── preprocess_audio.py
├── process_single_input.py
├── tune_threshold.py
├── README.md
├── STARTUP_INSTRUCTIONS.md
├── STRUCTURE.md
├── train_metadata.csv
├── train_metadata_rating_filtered.csv
├── train_metadata_duration_filtered.csv
├── train_metadata_merged_features.csv
├── bird_wikipedia_info_final.csv
├── eBird_Taxonomy_v2021.csv
├── sample_submission.csv
