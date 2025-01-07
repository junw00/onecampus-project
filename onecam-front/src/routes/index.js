import React from "react";
import { Route, Routes } from "react-router-dom";
import { Main } from "./pages/Main";

const Router = () => {

    return (
        <div className="app">
            <Routes>
                <Route path="/" element={<Main/>}/>
            </Routes>
        </div>
    )
}

export default Router;