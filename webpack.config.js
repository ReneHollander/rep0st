const CssMinimizerWebpackPlugin = require('css-minimizer-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const TerserWebpackPlugin = require('terser-webpack-plugin');
const { merge } = require('webpack-merge');
const { WebpackManifestPlugin } = require('webpack-manifest-plugin');
const path = require('path');

const commonConfig = (mode) => ({
    entry: {
        'main': './rep0st/web/frontend/main/main.js',
    },
    module: {
        rules: [
            {
                test: /\.(sa|sc|c)ss$/i,
                use: [
                    MiniCssExtractPlugin.loader,
                    "css-loader",
                ],
            },
            {
                test: /\.(png|svg|jpg|jpeg|gif)$/i,
                type: 'asset/resource',
            },
        ],
    },
    plugins: [
        new MiniCssExtractPlugin({
            filename: mode === 'development' ? '[name].css' : '[name].[contenthash].css',
        }),
        new WebpackManifestPlugin(),
    ],
    output: {
        path: path.resolve(__dirname, './rep0st/web/frontend/static'),
        clean: true,
        iife: true,
        publicPath: '',
    },
});

const productionConfig = {
    optimization: {
        minimizer: [
            new CssMinimizerWebpackPlugin(),
            new TerserWebpackPlugin(),
        ],
    },
    output: {
        filename: '[name].[contenthash].js',
    }
};

const developmentConfig = {
    devtool: 'inline-source-map',
    output: {
        filename: '[name].js',
    },
};

module.exports = (env, args) => {
    switch (args.mode) {
        case 'development':
            return merge(commonConfig(args.mode), developmentConfig);
        case 'production':
            return merge(commonConfig(args.mode), productionConfig);
        default:
            throw new Error('No matching configuration was found!');
    }
}
