import os
import sys
import numpy as np
import pandas as pd
import json
import umap
from typing import Tuple, List
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from dataclasses import dataclass
import matplotlib.pyplot as plt
import openai
from dotenv import load_dotenv
load_dotenv()

@dataclass
class ClusteringConfig:
    min_clusters: int = 3  
    max_clusters: int = 15
    random_state: int = 42
    umap_n_components: int = 2
    umap_n_neighbors: int = 50
    umap_min_dist: float = 0.02
    openai_model: str = "text-embedding-3-small"  # OpenAI embedding model

class Cluster:
    def __init__(self, config: ClusteringConfig = ClusteringConfig(), api_key: str = None):
        self.config = config
        # Set OpenAI API key
        if api_key:
            openai.api_key = api_key
        elif os.environ.get("OPENAI_API_KEY"):
            openai.api_key = os.environ.get("OPENAI_API_KEY")
        else:
            raise ValueError("OpenAI API key must be provided or set as OPENAI_API_KEY environment variable")
        
        self.client = openai.Client()

    def kmeans_clustering(self, n_clusters: int, embeddings: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        model = KMeans(
            n_clusters=n_clusters,
            init='k-means++',
            random_state=self.config.random_state,
            n_init=10
        )
        model.fit(embeddings)
        return model.labels_, model.cluster_centers_

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Use OpenAI's API to get embeddings for the provided texts"""
        try:
            # Process in batches if there are many texts (OpenAI has rate limits)
            batch_size = 100  # Adjust based on your needs and rate limits
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                
                # Call OpenAI API to get embeddings
                response = self.client.embeddings.create(
                    model=self.config.openai_model,
                    input=batch_texts
                )
                
                # Extract embedding vectors from the response
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            # Convert to numpy array
            return np.array(all_embeddings)
            
        except Exception as e:
            raise Exception(f"Error getting embeddings from OpenAI: {str(e)}")

    def reduce_dimensions(self, embeddings: np.ndarray) -> np.ndarray:
        n_samples = embeddings.shape[0]
        safe_n_neighbors = min(self.config.umap_n_neighbors, n_samples - 1)
        reducer = umap.UMAP(
            n_components=self.config.umap_n_components,
            n_neighbors=safe_n_neighbors,
            min_dist=self.config.umap_min_dist,
            random_state=self.config.random_state
        )
        return reducer.fit_transform(embeddings)

    def find_optimal_clusters(self, embeddings: np.ndarray) -> int:
        n_samples = embeddings.shape[0]
        
        # Adjust max_clusters based on sample size
        max_clusters = min(int(self.config.max_clusters), int(n_samples) - 1)
        min_clusters = min(int(self.config.min_clusters), int(max_clusters) - 1)
        
        if max_clusters <= min_clusters:
            return min_clusters
            
        inertias = []
        
        for n_clusters in range(min_clusters, max_clusters + 1):
            kmeans = KMeans(
                n_clusters=n_clusters,
                init='k-means++',
                random_state=self.config.random_state,
                n_init=10
            )
            kmeans.fit(embeddings)
            inertias.append(kmeans.inertia_)

        # Find elbow point using the percentage of variance explained
        inertias = np.array(inertias)
        diffs = np.diff(inertias)
        diffs_r = diffs[1:] / diffs[:-1]
        
        if len(diffs_r) > 0:
            elbow_point = np.argmin(diffs_r) + min_clusters + 1
        else:
            elbow_point = min_clusters

        return min(elbow_point, max_clusters)

    def find_optimal_clusters_silhouette(self, embeddings: np.ndarray) -> int:
        try:
            n_samples = embeddings.shape[0]

            # Adjust max_clusters based on sample size
            max_clusters = min(self.config.max_clusters, n_samples - 1)
            min_clusters = min(self.config.min_clusters, max_clusters - 1)

            if max_clusters <= min_clusters:
                print(f"Sample size too small, using {min_clusters} clusters")
                return min_clusters

            best_n_clusters = min_clusters
            best_silhouette = -1
            silhouette_scores = []

            cluster_range = range(min_clusters, max_clusters + 1)

            for n_clusters in cluster_range:
                try:
                    kmeans = KMeans(
                        n_clusters=n_clusters,
                        init="k-means++",
                        random_state=self.config.random_state,
                        n_init=10
                    )
                    cluster_labels = kmeans.fit_predict(embeddings)
                    
                    # Silhouette score requires at least 2 clusters
                    if len(np.unique(cluster_labels)) < 2:
                        print(f"Only one cluster formed with n_clusters={n_clusters}, skipping")
                        continue
                        
                    silhouette_avg = silhouette_score(embeddings, cluster_labels)
                    silhouette_scores.append(silhouette_avg)

                    if silhouette_avg > best_silhouette:
                        best_silhouette = silhouette_avg
                        best_n_clusters = n_clusters
                        
                except Exception as e:
                    print(f"Error during clustering with {n_clusters} clusters: {str(e)}")
                    continue

            # If we couldn't calculate any silhouette scores
            if not silhouette_scores:
                print("Could not calculate silhouette scores, using minimum clusters")
                return min_clusters
                
            print(f"Silhouette scores: {silhouette_scores}")
            print(f"Best number of clusters: {best_n_clusters} with silhouette score: {best_silhouette}")
            return best_n_clusters
            
        except Exception as e:
            print(f"Error in find_optimal_clusters_silhouette: {str(e)}")
            # Fallback to minimum clusters as default
            return self.config.min_clusters

    def process_clustering(self, data_path: str, metadata_column: str) -> dict:
        try:               
            if not isinstance(data_path, list):
                raise ValueError("Input data must be a list of records")

            df = pd.DataFrame(data_path)
            print(df)
            
            if metadata_column not in df.columns:
                raise ValueError(f"Column '{metadata_column}' not found in data")
            
            # Dynamically adjust clustering configuration based on data size
            n_samples = len(df)
            print(f"Dataset contains {n_samples} samples")
        
            # Adjust cluster settings based on data size
            if n_samples <= 200:
                self.config.min_clusters = 2
                self.config.max_clusters = 7
                print(f"Small dataset detected: min_clusters={self.config.min_clusters}, max_clusters={self.config.max_clusters}")
            elif n_samples >= 800:
                self.config.min_clusters = 5
                self.config.max_clusters = 30
                print(f"Large dataset detected: min_clusters={self.config.min_clusters}, max_clusters={self.config.max_clusters}")
            
            # Validate sample size
            if n_samples < 10:
                raise ValueError("Need at least 10 samples for clustering")
            # Process clustering with OpenAI embeddings
            embeddings = self.embed_texts(df[metadata_column].values)
            print(f"Generated embeddings with shape: {embeddings.shape}")
            
            reduced_embeddings = self.reduce_dimensions(embeddings)
            print(f"Reduced embeddings with shape: {reduced_embeddings.shape}")
            

            optimal_clusters = self.find_optimal_clusters_silhouette(reduced_embeddings)
            print(f"Optimal cluster count: {optimal_clusters}")
            
            labels, centers = self.kmeans_clustering(optimal_clusters, reduced_embeddings)
            
            # Add cluster labels to DataFrame
            df['cluster'] = labels

            # Prepare results
            results = {
                'optimal_clusters': optimal_clusters,
                'cluster_labels': labels.tolist(),
                'cluster_centers': centers.tolist(),
                'reduced_embeddings': reduced_embeddings.tolist()
            }

            print(f"Clustering complete with {optimal_clusters} clusters")
            
            json_string = df.to_json(orient='records', lines=False)
            return json_string, optimal_clusters

        except Exception as e:
            raise Exception(f"Clustering pipeline failed: {str(e)}") from e

# Example usage:
# if __name__ == "__main__":
#     # Create configuration
#     config = ClusteringConfig(
#         min_clusters=4,  
#         max_clusters=20,
#         random_state=42,
#         openai_model="text-embedding-3-small"  # You can also use "text-embedding-3-large" or "text-embedding-ada-002"
#     )
    
#     # Initialize with your API key
#     print(os.getenv("OPENAI_API_KEY"))
#     print(os.environ.get("OPENAI_API_KEY"))
#     api_key = os.getenv("OPENAI_API_KEY") 
#     clusterer = Cluster(config, api_key)
    
#     # Example data and column
#     metadata_column = "Keyword"
    
#     # Either load from file:
#     # df = pd.read_csv("your_data.csv")
#     # data = df.to_dict(orient="records")
    
#     # Or create sample data:
#     data = [
#         {"Keyword": "machine learning algorithms"},
#         {"Keyword": "deep learning neural networks"},
#         {"Keyword": "data science projects"},
#         {"Keyword": "python programming tutorials"},
#         {"Keyword": "javascript frameworks comparison"},
#         {"Keyword": "react vs angular"},
#         {"Keyword": "vue.js for beginners"},
#         {"Keyword": "web development best practices"},
#         {"Keyword": "database optimization techniques"},
#         {"Keyword": "sql query performance"}
#     ]
    
#     try:
#         results, optimal_clusters = clusterer.process_clustering(data, metadata_column)
#         print(f"Results: {results}")
#         print(f"Optimal number of clusters: {optimal_clusters}")
#     except Exception as e:
#         print(f"Error: {str(e)}")
