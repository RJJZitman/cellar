# API

## **API configuration**

### *Getting Started* 
1. Run the live server 

    ```bash
    uvicorn src.api.main:app --reload 
    ```

2. Open the Swagger UI

    ```bash
    http://127.0.0.01:8000/login
    ```

### *Structure API* 

| Folder          | Python file         | Contents                                                            |
|-----------------|---------------------|---------------------------------------------------------------------|
| src/api/        |                     |                                                                     |
|                 | main                | An instance of the class FastAPI is created and routers are linked. |
|                 | constants           | Defining of constant values                                         |
|                 | dependencies        | Dependency injection                                                |  
| src/api/routers |                     |                                                                     | 
|                 | users_router        | 	A...                                                               | 
|                 | cellar_router       | 	...                                                                | 
|                 | cellar_views_router | 	...                                                                | 

### *users*

#### ::: src.api.routers.users_router

### *cellar*

#### ::: src.api.routers.cellar_router

### *cellar_views*

#### ::: src.api.routers.cellar_views_router

## API choices
### FastAPI 
...

### Partition Key and ID in the cosmos DB 


### Authentication

oath2
