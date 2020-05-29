import React from "react";
import fs from 'fs';
import path from 'path';
import matter from "gray-matter";
import Head from "next/head";
import marked from 'marked';
import Jumbotron from 'react-bootstrap/Jumbotron'
import Container from 'react-bootstrap/Container'
import Row from 'react-bootstrap/Row'
import Col from 'react-bootstrap/Col'

const Post = ({ htmlContent, data }) => {
  return (
    <>
    <Head>
      <title>{data.title}</title>
      <meta title='description' content={data.descrpitpion}/>
    </Head>
    <Jumbotron>
      <h1>{data.title}</h1>
        <p>
          {data.description} <small className="text-muted">{data.date}</small>
        </p>
    </Jumbotron>
      <Container>
        <Row>
          <Col>
            <div dangerouslySetInnerHTML={{__html: htmlContent }} />
          </Col>
        </Row>
      </Container>
    </>
  )
}

export const getStaticPaths = async () => {

  const files = fs.readdirSync('posts', {withFileTypes: false})

  const paths = files.map(filename => {
      return {
        params: {
          slug: filename.replace('.md', '')
        },
      }
    })


  return {
    paths,
    fallback: false,
  }
}

export const getStaticProps = async ({params: { slug }}) => {

  const contents = fs.readFileSync(path.join('posts', slug + '.md')).toString()
  const parsedMarkdown = matter(contents)
  const htmlContent = marked(parsedMarkdown.content)
  
  return {
    props: {
      htmlContent,
      data: parsedMarkdown.data,
    }
  }
}

export default Post
